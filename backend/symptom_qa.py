"""Symptom Q&A bridge — question on dashboard, Claude answers via MCP (no API)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.paths import active_profile_id, ensure_health_folders


def _pending_path(profile_id: str | None = None) -> Path:
    return ensure_health_folders(profile_id) / "data" / "pending_symptom_question.json"


def _answer_path(profile_id: str | None = None) -> Path:
    return ensure_health_folders(profile_id) / "reports" / "symptom_answer.json"


def request_symptom_question(question: str, profile_id: str | None = None) -> dict[str, Any]:
    q = (question or "").strip()
    if len(q) < 2:
        return {"ok": False, "error": "question_too_short"}
    path = _pending_path(profile_id)
    payload = {
        "status": "pending",
        "question": q,
        "requested_at": datetime.now().isoformat(timespec="seconds"),
        "profile_id": profile_id or active_profile_id(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "pending": True, **payload}


def get_symptom_question(profile_id: str | None = None) -> dict[str, Any]:
    path = _pending_path(profile_id)
    if not path.exists():
        return {"pending": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pending": False}
    if data.get("status") != "pending":
        return {"pending": False}
    return {
        "pending": True,
        "question": data.get("question", ""),
        "requested_at": data.get("requested_at"),
        "instruction_ru": (
            "На дашборде задан вопрос о симптоме. Сначала get_symptom_question(). "
            "Затем get_lab_results, get_checkin_history, get_clinical_context. "
            "Ответ: 2–4 коротких абзаца по-русски, тепло, без диагноза. "
            "Обязательно save_symptom_answer с полями summary_ru, possible_links_ru (список), "
            "evidence (массив: claim_ru, kind, source_label, study_url если есть), "
            "discuss_with_doctor_ru. Затем refresh_dashboard_file. "
            "Ответ пользователю одним предложением: «Ответ на дашборде»."
        ),
    }


def save_symptom_answer(
    summary_ru: str,
    possible_links_ru: list[str] | None = None,
    evidence: list[dict] | None = None,
    discuss_with_doctor_ru: str = "",
    attachments: list[str] | None = None,
    mode: str | None = None,
    question: str | None = None,
    profile_id: str | None = None,
    # bilingual extras
    summary_en: str = "",
    possible_links_en: list[str] | None = None,
    discuss_with_doctor_en: str = "",
) -> dict[str, Any]:
    from backend.consilium_format import normalize_evidence

    q = (question or "").strip()
    pending = _pending_path(profile_id)
    if not q:
        if pending.exists():
            try:
                q = json.loads(pending.read_text(encoding="utf-8")).get("question", "")
            except json.JSONDecodeError:
                pass

    data: dict[str, Any] = {
        "question": q,
        "summary_ru": (summary_ru or "").strip(),
        "summary_en": (summary_en or "").strip(),
        "possible_links_ru": [str(x).strip() for x in (possible_links_ru or []) if str(x).strip()],
        "possible_links_en": [str(x).strip() for x in (possible_links_en or []) if str(x).strip()],
        "evidence": normalize_evidence(evidence or []),
        "discuss_with_doctor_ru": (discuss_with_doctor_ru or "").strip(),
        "discuss_with_doctor_en": (discuss_with_doctor_en or "").strip(),
        "answered_at": datetime.now().isoformat(timespec="seconds"),
        "saved_to_history": False,
        "attachments": [str(a).strip() for a in (attachments or []) if str(a).strip()],
    }
    if mode:
        data["mode"] = mode
    path = _answer_path(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if pending.exists():
        pending.write_text(
            json.dumps({"status": "done", "completed_at": data["answered_at"]}, ensure_ascii=False),
            encoding="utf-8",
        )

    from backend.dashboard_export import export_dashboard_html

    export_dashboard_html(profile_id)
    return {"ok": True, "path": str(path)}


def load_symptom_answer(profile_id: str | None = None) -> dict[str, Any] | None:
    path = _answer_path(profile_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def symptom_qa_status(profile_id: str | None = None) -> dict[str, Any]:
    req = get_symptom_question(profile_id)
    ans = load_symptom_answer(profile_id)
    return {
        "pending": req.get("pending", False),
        "pending_question": req.get("question") if req.get("pending") else None,
        "has_answer": ans is not None,
        "answer": ans,
    }
