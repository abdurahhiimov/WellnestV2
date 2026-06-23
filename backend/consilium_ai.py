"""Claude consilium bridge — request on dashboard, Claude saves via MCP (no API)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import health_db
from backend.consilium import SECTION_LABELS, SPECIALIST_ROLES, build_consilium_html_from_data
from backend.paths import active_profile_id, ensure_health_folders, health_root

from backend.consilium_format import normalize_opinion as _normalize_opinion_full

OPINION_KEYS = ("see", "concerns", "recommendations", "reasoning", "evidence")
SPECIALIST_IDS = {r[0] for r in SPECIALIST_ROLES}
DEFAULT_FOCUS = {r[0]: r[3] for r in SPECIALIST_ROLES}
DEFAULT_TITLES = {r[0]: (r[1], r[2]) for r in SPECIALIST_ROLES}


def _pending_path(profile_id: str | None = None) -> Path:
    return ensure_health_folders(profile_id) / "data" / "pending_consilium.json"


def _ai_json_path(profile_id: str | None = None) -> Path:
    return ensure_health_folders(profile_id) / "reports" / "consilium_ai.json"


def _normalize_opinion(raw: dict | None) -> dict[str, Any]:
    return _normalize_opinion_full(raw)


def _normalize_specialists(specialists: list[dict]) -> list[dict[str, Any]]:
    by_id: dict[str, dict] = {}
    for sp in specialists:
        sid = sp.get("id") or ""
        if sid not in SPECIALIST_IDS:
            continue
        title_ru, title_en = DEFAULT_TITLES[sid]
        by_id[sid] = {
            "id": sid,
            "title_ru": sp.get("title_ru") or title_ru,
            "title_en": sp.get("title_en") or title_en,
            "focus_ru": sp.get("focus_ru") or DEFAULT_FOCUS[sid],
            "opinion": _normalize_opinion(sp.get("opinion")),
        }
    ordered = []
    for sid, _, _, _ in SPECIALIST_ROLES:
        if sid in by_id:
            ordered.append(by_id[sid])
    if len(ordered) < 1:
        raise ValueError(f"No valid specialists to save; got {[s['id'] for s in ordered]}")
    return ordered


def request_claude_consilium(profile_id: str | None = None) -> dict[str, Any]:
    """Dashboard calls this — creates a pending flag for Claude MCP."""
    path = _pending_path(profile_id)
    payload = {
        "status": "pending",
        "requested_at": datetime.now().isoformat(timespec="seconds"),
        "profile_id": profile_id or active_profile_id(),
        "hint_ru": "Откройте Claude Desktop → проект «Здоровье Замиры» и напишите «готово» или «консилиум».",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "pending": True, **payload}


def get_consilium_request(profile_id: str | None = None) -> dict[str, Any]:
    path = _pending_path(profile_id)
    if not path.exists():
        return {"pending": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pending": False}
    if data.get("status") != "pending":
        return {"pending": False}

    from backend.clinical_history import build_consilium_briefing

    briefing = build_consilium_briefing(profile_id)
    return {
        "pending": True,
        "requested_at": data.get("requested_at"),
        "briefing": briefing,
        "instruction_ru": (
            "ПОЛНЫЙ КОНСИЛИУМ — уровень живых врачей. НЕ шаблон «обсудите с врачом».\n"
            "1) briefing ниже + get_lab_results, get_tasks, get_checkin_history\n"
            "2) Каждый врач (endo,gyn,neuro,nutri,ortho,gp): see 3–8 предложений с цифрами и динамикой; "
            "concerns конкретно; recommendations мин.2 actionable (доза/срок); evidence мин.2 с study_url\n"
            "3) save_claude_consilium_report — если quality issues, переписать глубже\n"
            "4) refresh_dashboard_file. Ответ: «Готово, полный консилиум на дашборде»."
        ),
    }


def save_claude_consilium_report(
    specialists: list[dict],
    profile_id: str | None = None,
) -> dict[str, Any]:
    profile = health_db.get_patient_profile(profile_id)
    meds = health_db.get_medications(profile_id)
    from backend.weekly_brief import build_weekly_brief

    brief = build_weekly_brief(profile_id)
    normalized = _normalize_specialists(specialists)

    from backend.consilium_quality import validate_consilium

    quality = validate_consilium(normalized)

    data: dict[str, Any] = {
        "source": "claude",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "patient": profile.get("display_name"),
        "medications_summary": ", ".join(m["name"] for m in meds[:8]),
        "headline_ru": brief.get("headline_ru", ""),
        "section_labels": SECTION_LABELS,
        "specialists": normalized,
        "quality": quality,
    }

    root = ensure_health_folders(profile_id)
    json_path = _ai_json_path(profile_id)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    html_path = root / "reports" / "consilium_ai.html"
    html_path.write_text(
        build_consilium_html_from_data(data, footer_note="Разбор подготовлен Claude (локально, без облачного API)."),
        encoding="utf-8",
    )

    pending = _pending_path(profile_id)
    if pending.exists():
        pending.write_text(
            json.dumps({"status": "done", "completed_at": data["generated_at"]}, ensure_ascii=False),
            encoding="utf-8",
        )

    from backend.dashboard_export import export_dashboard_html

    export_dashboard_html(profile_id)
    return {
        "ok": True,
        "quality": quality,
        "json_path": str(json_path),
        "html_path": str(html_path),
        "dashboard_url": "http://127.0.0.1:8787/dashboard#consilium-panel",
    }


def load_claude_consilium(profile_id: str | None = None) -> dict[str, Any] | None:
    path = _ai_json_path(profile_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for sp in data.get("specialists") or []:
        if isinstance(sp.get("opinion"), dict):
            sp["opinion"] = _normalize_opinion(sp["opinion"])
    return data


def consilium_status(profile_id: str | None = None) -> dict[str, Any]:
    req = get_consilium_request(profile_id)
    ai = load_claude_consilium(profile_id)
    return {
        "claude_pending": req.get("pending", False),
        "requested_at": req.get("requested_at"),
        "has_claude_report": ai is not None,
        "claude_generated_at": ai.get("generated_at") if ai else None,
        "claude_report": ai,
    }
