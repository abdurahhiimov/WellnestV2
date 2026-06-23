"""Evening check-ins — mood, sleep, symptoms."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from backend import health_db

KIND = "evening_checkin"


def save_evening_checkin(
    mood: int = 3,
    sleep_quality: int = 3,
    symptoms: list[str] | None = None,
    notes: str = "",
    checkin_date: str | None = None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    mood = max(1, min(5, int(mood)))
    sleep_quality = max(1, min(5, int(sleep_quality)))
    day = checkin_date or date.today().isoformat()
    symptoms = symptoms or []
    day_score = round((mood + sleep_quality) / 2)

    payload = {
        "kind": KIND,
        "mood": mood,
        "sleep_quality": sleep_quality,
        "symptoms": symptoms,
        "notes": notes.strip(),
    }
    summary_parts = [f"Настроение {mood}/5", f"Сон {sleep_quality}/5"]
    if symptoms:
        summary_parts.append(", ".join(symptoms[:3]))
    summary_ru = " · ".join(summary_parts)

    conn = health_db.connect(profile_id)
    existing = conn.execute(
        "SELECT id FROM checkins WHERE checkin_date = ?",
        (day,),
    ).fetchone()
    now = datetime.utcnow().isoformat()
    if existing:
        conn.execute(
            """
            UPDATE checkins SET day_score = ?, summary_ru = ?, raw_json = ?, created_at = ?
            WHERE checkin_date = ?
            """,
            (day_score, summary_ru, json.dumps(payload, ensure_ascii=False), now, day),
        )
    else:
        conn.execute(
            """
            INSERT INTO checkins(checkin_date, day_score, summary_ru, raw_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (day, day_score, summary_ru, json.dumps(payload, ensure_ascii=False), now),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "checkin_date": day, "day_score": day_score, "summary_ru": summary_ru}


def get_checkins(days: int = 14, profile_id: str | None = None) -> list[dict[str, Any]]:
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    conn = health_db.connect(profile_id)
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM checkins WHERE checkin_date >= ? ORDER BY checkin_date DESC",
            (since,),
        )
    ]
    conn.close()
    out = []
    for row in rows:
        item = dict(row)
        try:
            raw = json.loads(row.get("raw_json") or "{}")
        except json.JSONDecodeError:
            raw = {}
        if raw.get("kind") != KIND and raw.get("kind") is not None and "mood" not in raw:
            # legacy symptom-only row
            raw.setdefault("mood", row.get("day_score") or 3)
            raw.setdefault("sleep_quality", 3)
        item["payload"] = raw
        out.append(item)
    return out


def checkin_dashboard(days: int = 7, profile_id: str | None = None) -> dict[str, Any]:
    recent = get_checkins(days=days, profile_id=profile_id)
    series = []
    for row in reversed(recent):
        p = row.get("payload") or {}
        series.append({
            "date": row["checkin_date"],
            "mood": p.get("mood", row.get("day_score")),
            "sleep_quality": p.get("sleep_quality"),
            "symptoms": p.get("symptoms") or [],
            "notes": p.get("notes") or row.get("summary_ru", ""),
        })
    today = date.today().isoformat()
    has_today = any(r["checkin_date"] == today for r in recent)
    return {
        "has_today": has_today,
        "recent": series,
        "latest": series[-1] if series else None,
        "count": len(series),
    }
