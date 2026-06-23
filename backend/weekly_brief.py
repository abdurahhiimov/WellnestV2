"""Weekly brief — what matters this week on the dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend import health_db

CRITICAL_LABS = ("prolactin", "tsh", "estradiol", "vitamin_d")


def _latest_labs(profile_id: str | None) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in health_db.get_lab_results(limit=200, profile_id=profile_id):
        code = row["test_code"]
        if code not in latest or row["sample_date"] >= latest[code]["sample_date"]:
            latest[code] = row
    return latest


def build_weekly_brief(profile_id: str | None = None) -> dict[str, Any]:
    tasks = health_db.get_tasks(profile_id)
    latest = _latest_labs(profile_id)
    items: list[dict[str, str]] = []

    for t in tasks:
        if t["priority"] == "urgent":
            items.append({
                "kind": "task",
                "priority": "urgent",
                "text_ru": f"Срочно: {t['title_ru']}",
                "text_en": f"Urgent: {t['title_ru']}",
            })

    important = [t for t in tasks if t["priority"] == "important"][:3]
    for t in important:
        items.append({
            "kind": "task",
            "priority": "important",
            "text_ru": t["title_ru"],
            "text_en": t["title_ru"],
        })

    for code in CRITICAL_LABS:
        row = latest.get(code)
        if not row:
            continue
        flag = row.get("flag")
        fresh = row.get("freshness", {})
        name = row.get("test_name_ru", code)
        val = row.get("value") if row.get("value") is not None else row.get("value_text", "—")
        unit = row.get("unit") or ""

        if flag in ("low", "high"):
            arrow = "↓" if flag == "low" else "↑"
            items.append({
                "kind": "lab_flag",
                "priority": "warn" if flag == "high" else "caution",
                "text_ru": f"{name} {val} {unit} {arrow} ({row['sample_date']})",
                "text_en": f"{name} {val} {unit} {arrow} ({row['sample_date']})",
            })
        elif fresh.get("status") in ("aging", "stale"):
            items.append({
                "kind": "lab_stale",
                "priority": "caution",
                "text_ru": f"Давно не сдавали: {name} (последний — {row['sample_date']})",
                "text_en": f"Overdue recheck: {name} (last — {row['sample_date']})",
            })

    if not items:
        headline_ru = "На этой неделе всё под контролем — следите за задачами и новыми анализами."
        headline_en = "This week looks stable — keep up with tasks and new labs."
    elif any(i["priority"] == "urgent" for i in items):
        headline_ru = "На этой неделе есть срочные пункты — см. ниже."
        headline_en = "There are urgent items this week — see below."
    else:
        headline_ru = "На этой неделе стоит обратить внимание на отмеченные пункты."
        headline_en = "A few items need attention this week."

    return {
        "headline_ru": headline_ru,
        "headline_en": headline_en,
        "items": items[:8],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
