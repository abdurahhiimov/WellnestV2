"""Shared locale strings for printable HTML reports."""

from __future__ import annotations

from typing import Any

LANGS = ("ru", "en")

DIAGNOSIS_EN: dict[str, str] = {
    "prolactinoma": "Prolactinoma (pituitary microadenoma)",
    "hashimoto": "Hypothyroidism / Hashimoto's thyroiditis",
    "menopause": "Menopause",
}

TEST_NAME_EN: dict[str, str] = {
    "prolactin": "Prolactin",
    "tsh": "TSH",
    "ft4": "Free T4",
    "estradiol": "Estradiol",
    "vitamin_d": "Vitamin D",
    "ferritin": "Ferritin",
    "hemoglobin": "Hemoglobin",
    "hematocrit": "Hematocrit",
    "neutrophils": "Neutrophils",
    "lymphocytes": "Lymphocytes",
    "platelets": "Platelets",
    "wbc": "White blood cells",
}

PURPOSE: dict[str, dict[str, str]] = {
    "prolactinoma": {"ru": "пролактинома", "en": "prolactinoma"},
    "hypothyroidism": {"ru": "гипотиреоз", "en": "hypothyroidism"},
    "HRT / menopause": {"ru": "ЗГТ / менопауза", "en": "HRT / menopause"},
    "HRT": {"ru": "ЗГТ", "en": "HRT"},
}

PRIORITY: dict[str, dict[str, str]] = {
    "urgent": {"ru": "срочно", "en": "urgent"},
    "important": {"ru": "важно", "en": "important"},
    "high": {"ru": "важно", "en": "important"},
    "planned": {"ru": "планово", "en": "planned"},
    "routine": {"ru": "планово", "en": "planned"},
    "normal": {"ru": "обычный", "en": "normal"},
}

CATEGORY: dict[str, dict[str, str]] = {
    "imaging": {"ru": "обследование", "en": "imaging"},
    "labs": {"ru": "анализы", "en": "labs"},
    "visit": {"ru": "визит", "en": "visit"},
    "meds": {"ru": "препараты", "en": "medications"},
    "lifestyle": {"ru": "образ жизни", "en": "lifestyle"},
}

FLAG: dict[str, dict[str, str]] = {
    "normal": {"ru": "норма", "en": "normal"},
    "low": {"ru": "ниже", "en": "low"},
    "high": {"ru": "выше", "en": "high"},
}


def normalize_lang(lang: str | None) -> str:
    return lang if lang in LANGS else "ru"


def flag_label(flag: str | None, lang: str) -> str:
    lang = normalize_lang(lang)
    key = (flag or "normal").lower()
    return FLAG.get(key, FLAG["normal"])[lang]


def priority_label(priority: str, lang: str) -> str:
    lang = normalize_lang(lang)
    return PRIORITY.get(priority, {"ru": priority, "en": priority})[lang]


def category_label(category: str | None, lang: str) -> str:
    lang = normalize_lang(lang)
    key = category or ""
    return CATEGORY.get(key, {"ru": key or "—", "en": key or "—"})[lang]


def purpose_label(purpose: str | None, lang: str) -> str:
    lang = normalize_lang(lang)
    key = purpose or ""
    if key in PURPOSE:
        return PURPOSE[key][lang]
    return key or "—"


def diagnosis_label(dx: dict[str, Any], lang: str) -> str:
    lang = normalize_lang(lang)
    if lang == "en":
        code = dx.get("code") or ""
        return DIAGNOSIS_EN.get(code, dx.get("label_ru") or code or "—")
    return dx.get("label_ru") or dx.get("code") or "—"


def test_name(row: dict[str, Any], lang: str) -> str:
    lang = normalize_lang(lang)
    if lang == "ru":
        return row.get("test_name_ru") or row.get("test_code") or "—"
    code = row.get("test_code") or ""
    return TEST_NAME_EN.get(code, row.get("test_name_ru") or code or "—")


VISIT_PACK: dict[str, dict[str, str]] = {
    "ru": {
        "title": "Пакет для врача",
        "visit": "визит к врачу",
        "generated": "Сформировано",
        "local_data": "Wellnest (локальные данные)",
        "diagnoses": "Диагнозы",
        "this_week": "На этой неделе",
        "no_urgent": "Нет срочных пунктов",
        "meds": "Препараты",
        "med_name": "Препарат",
        "dose": "Доза",
        "purpose": "Назначение",
        "labs": "Последние анализы",
        "date": "Дата",
        "test": "Тест",
        "value": "Значение",
        "flag": "Флаг",
        "tasks": "Открытые задачи",
        "task": "Задача",
        "priority": "Приоритет",
        "category": "Категория",
        "questions": "Вопросы врачу",
        "disclaimer": "Не является медицинским заключением. Обсудите все пункты с лечащим врачом.",
        "print_hint": "← Дашборд · Cmd+P → Сохранить как PDF",
        "q1": "Нужно ли корректировать дозу Эутирокса по последнему ТТГ?",
        "q2": "Эстрадиол в норме на фоне Дивигеля?",
        "q3": "Пролактин — продолжать текущую схему Достинекса?",
        "q4": "Нужна ли коррекция витамина D и железа?",
        "q5": "Когда повторить УЗИ / МРТ из списка задач?",
    },
    "en": {
        "title": "Doctor visit pack",
        "visit": "doctor visit",
        "generated": "Generated",
        "local_data": "Wellnest (local data)",
        "diagnoses": "Diagnoses",
        "this_week": "This week",
        "no_urgent": "No urgent items",
        "meds": "Medications",
        "med_name": "Medication",
        "dose": "Dose",
        "purpose": "Indication",
        "labs": "Recent labs",
        "date": "Date",
        "test": "Test",
        "value": "Value",
        "flag": "Flag",
        "tasks": "Open tasks",
        "task": "Task",
        "priority": "Priority",
        "category": "Category",
        "questions": "Questions for your doctor",
        "disclaimer": "Not a medical conclusion. Discuss all items with your treating physician.",
        "print_hint": "← Dashboard · Cmd+P → Save as PDF",
        "q1": "Should Euthyrox dose be adjusted based on the latest TSH?",
        "q2": "Is estradiol adequate on Divigel?",
        "q3": "Prolactin — continue current Dostinex schedule?",
        "q4": "Should vitamin D and iron be corrected?",
        "q5": "When to repeat ultrasound / MRI from the task list?",
    },
}

SYMPTOM_REPORT: dict[str, dict[str, str]] = {
    "ru": {
        "title": "Симптом — отчёт",
        "generated": "Сформировано",
        "question": "Вопрос",
        "analysis": "Разбор",
        "links": "Возможные связи",
        "discuss": "Обсудить с врачом",
        "attachments": "Вложения",
        "disclaimer": "Не является медицинским диагнозом. Обсудите с лечащим врачом.",
    },
    "en": {
        "title": "Symptom report",
        "generated": "Generated",
        "question": "Question",
        "analysis": "Analysis",
        "links": "Possible links",
        "discuss": "Discuss with your doctor",
        "attachments": "Attachments",
        "disclaimer": "Not a medical diagnosis. Discuss with your treating physician.",
    },
}
