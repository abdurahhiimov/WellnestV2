"""Guided symptom survey — saves to evening check-in."""

from __future__ import annotations

from typing import Any

from backend.checkins import save_evening_checkin

# Default symptom chips — adjust per user profile.
SYMPTOM_CHIPS_RU = [
    {"id": "fatigue", "label": "Усталость"},
    {"id": "headache", "label": "Головная боль"},
    {"id": "dizziness", "label": "Головокружение"},
    {"id": "shoulder", "label": "Боль в плече"},
    {"id": "hot_flashes", "label": "Приливы"},
    {"id": "dryness", "label": "Сухость"},
    {"id": "nausea", "label": "Тошнота"},
    {"id": "anxiety", "label": "Тревога"},
]

SYMPTOM_CHIPS_EN = [
    {"id": "fatigue", "label": "Fatigue"},
    {"id": "headache", "label": "Headache"},
    {"id": "dizziness", "label": "Dizziness"},
    {"id": "shoulder", "label": "Shoulder pain"},
    {"id": "hot_flashes", "label": "Hot flashes"},
    {"id": "dryness", "label": "Dryness"},
    {"id": "nausea", "label": "Nausea"},
    {"id": "anxiety", "label": "Anxiety"},
]

SLEEP_MAP = {"good": 5, "ok": 3, "bad": 1}


def survey_config(profile_id: str | None = None) -> dict[str, Any]:
    from backend.profile_store import load_profile

    male = (load_profile(profile_id).get("sex") or "").lower() == "male"
    rested_ru = "Выспался" if male else "Выспалась"
    return {
        "steps": 4,
        "symptom_chips_ru": SYMPTOM_CHIPS_RU,
        "symptom_chips_en": SYMPTOM_CHIPS_EN,
        "mood_labels_ru": ["Очень плохо", "Плохо", "Нормально", "Хорошо", "Отлично"],
        "mood_labels_en": ["Very bad", "Bad", "OK", "Good", "Great"],
        "sleep_options_ru": [
            {"id": "good", "label": rested_ru, "emoji": "😴"},
            {"id": "ok", "label": "Так себе", "emoji": "😐"},
            {"id": "bad", "label": "Плохо", "emoji": "😩"},
        ],
        "sleep_options_en": [
            {"id": "good", "label": "Well rested", "emoji": "😴"},
            {"id": "ok", "label": "So-so", "emoji": "😐"},
            {"id": "bad", "label": "Poor sleep", "emoji": "😩"},
        ],
    }


def save_symptom_survey(
    mood: int,
    sleep: str,
    symptoms: list[str] | None = None,
    notes: str = "",
    profile_id: str | None = None,
) -> dict[str, Any]:
    sleep_quality = SLEEP_MAP.get(sleep, 3)
    labels = {c["id"]: c["label"] for c in SYMPTOM_CHIPS_RU}
    symptom_labels = [labels.get(s, s) for s in (symptoms or [])]
    result = save_evening_checkin(
        mood=max(1, min(5, int(mood))),
        sleep_quality=sleep_quality,
        symptoms=symptom_labels,
        notes=notes.strip(),
        profile_id=profile_id,
    )
    result["survey_saved"] = True
    return result
