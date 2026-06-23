"""Longitudinal clinical context + specialist personas for smart consilium."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.paths import health_root, profile_dir


def _load_personas_json(name: str, profile_id: str | None = None) -> dict:
    """Read a read-only template file from profiles/ (with default fallback)."""
    path = profile_dir(profile_id) / name
    if not path.exists():
        fallback = profile_dir("default") / name
        if fallback.exists():
            return json.loads(fallback.read_text(encoding="utf-8"))
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _clinical_history_path(profile_id: str | None = None) -> Path:
    """Clinical history lives in the user's HEALTH data folder, not in profiles/."""
    return health_root(profile_id) / "data" / "clinical_history.json"


def get_clinical_history(profile_id: str | None = None) -> dict[str, Any]:
    path = _clinical_history_path(profile_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_clinical_history(data: dict[str, Any], profile_id: str | None = None) -> None:
    path = _clinical_history_path(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_symptom_memory(
    question: str,
    answer: dict[str, Any],
    attachments: list[str] | None = None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Persist a symptom Q&A into clinical_history for future consilium context."""
    from datetime import datetime

    hist = get_clinical_history(profile_id)
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "question": (question or "").strip(),
        "summary_ru": (answer.get("summary_ru") or "").strip(),
        "possible_links_ru": answer.get("possible_links_ru") or [],
        "discuss_with_doctor_ru": (answer.get("discuss_with_doctor_ru") or "").strip(),
        "attachments": attachments or [],
    }
    mem = hist.setdefault("symptom_memory", [])
    mem.append(entry)
    hist["symptom_memory"] = mem[-50:]
    _save_clinical_history(hist, profile_id)

    from backend.symptom_qa import _answer_path

    ans_path = _answer_path(profile_id)
    if ans_path.exists():
        try:
            ans = json.loads(ans_path.read_text(encoding="utf-8"))
            ans["saved_to_history"] = True
            ans["saved_at"] = entry["at"]
            ans_path.write_text(json.dumps(ans, ensure_ascii=False, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            pass

    from backend.dashboard_export import export_dashboard_html

    export_dashboard_html(profile_id)
    return {"ok": True, "saved": True, "entries": len(hist["symptom_memory"])}


def get_specialist_personas(profile_id: str | None = None) -> dict[str, Any]:
    return _load_personas_json("specialist_personas.json", profile_id)


def get_persona(specialist_id: str, profile_id: str | None = None) -> dict[str, Any]:
    data = get_specialist_personas(profile_id)
    return (data.get("specialists") or {}).get(specialist_id) or {}


def lab_timeline(test_code: str | None = None, profile_id: str | None = None) -> list[dict]:
    hist = get_clinical_history(profile_id)
    rows = hist.get("lab_timeline") or []
    if test_code:
        return [r for r in rows if r.get("test_code") == test_code]
    return rows


def merge_labs_with_db(db_labs: list[dict], profile_id: str | None = None) -> list[dict]:
    """Combine health.db latest with historical timeline for Claude."""
    timeline = lab_timeline(profile_id=profile_id)
    by_code: dict[str, list[dict]] = {}
    for row in timeline:
        code = row.get("test_code") or "unknown"
        by_code.setdefault(code, []).append(row)
    for row in db_labs:
        code = row.get("test_code")
        if not code:
            continue
        entry = {
            "test_code": code,
            "test_name_ru": row.get("test_name_ru"),
            "value": row.get("value"),
            "unit": row.get("unit"),
            "sample_date": row.get("sample_date"),
            "source": "health.db",
            "flag": row.get("flag"),
        }
        by_code.setdefault(code, []).append(entry)
    out = []
    for code, rows in by_code.items():
        rows_sorted = sorted(rows, key=lambda r: str(r.get("sample_date") or ""))
        out.append({"test_code": code, "history": rows_sorted, "latest": rows_sorted[-1] if rows_sorted else None})
    return sorted(out, key=lambda x: x["test_code"])


def _briefing_panel(profile_id: str | None = None) -> list[str]:
    from backend.profile_store import load_profile

    panel = load_profile(profile_id).get("specialist_panel") or []
    return panel or ["endo", "gyn", "neuro", "nutri", "ortho", "gp"]


def build_consilium_briefing(profile_id: str | None = None) -> dict[str, Any]:
    from backend import health_db
    from backend.medical_graph import build_medical_graph
    from backend.profile_store import load_profile
    from backend.reference_db import clinical_context_for_patient

    profile = health_db.get_patient_profile(profile_id)
    user_profile = load_profile(profile_id)
    hist = get_clinical_history(profile_id)
    personas = get_specialist_personas(profile_id)
    return {
        "medical_graph": build_medical_graph(user_profile),
        "allergies": user_profile.get("allergies") or [],
        "family_history": user_profile.get("family_history") or [],
        "immunizations": user_profile.get("immunizations") or [],
        "procedures": user_profile.get("procedures") or [],
        "quality_bar": hist.get("quality_bar_ru"),
        "quality_rules": personas.get("quality_rules"),
        "symptoms_active": hist.get("symptoms_active"),
        "symptom_memory": (hist.get("symptom_memory") or [])[-10:],
        "clinical_events": hist.get("clinical_events"),
        "imaging": hist.get("imaging"),
        "medications_full": hist.get("medications_full"),
        "nutraceuticals": hist.get("nutraceuticals"),
        "therapeutic_targets": hist.get("therapeutic_targets"),
        "pending_diagnostics_critical": hist.get("pending_diagnostics_critical"),
        "lab_timeline_merged": merge_labs_with_db(health_db.get_lab_results(limit=100, profile_id=profile_id), profile_id),
        "reference_context": clinical_context_for_patient(profile),
        "specialist_checklists": {
            sid: get_persona(sid, profile_id) for sid in _briefing_panel(profile_id)
        },
        "instruction_ru": (
            "Пишите как живые врачи из personas. Минимум — уровень примера MDT: цифры+даты, динамика, "
            "механизмы простым языком, конкретные рекомендации (дозы/сроки/что не трогать). "
            "Запрещено: только «обсудите с врачом» без конкретики."
        ),
    }
