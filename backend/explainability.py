"""Static + dynamic explainability copy for dashboard (? buttons)."""

from __future__ import annotations

from typing import Any

TEST_LABELS: dict[str, str] = {
    "prolactin": "Пролактин",
    "tsh": "ТТГ",
    "ft4": "Свободный Т4",
    "estradiol": "Эстрадиол",
    "vitamin_d": "Витамин D",
    "ferritin": "Ферритин",
    "hemoglobin": "Гемоглобин",
    "hematocrit": "Гематокрит",
}

STATUS_LABELS: dict[str, str] = {
    "good": "В норме",
    "caution": "Есть отклонение — наблюдать",
    "warn": "Несколько отклонений — обсудить с врачом",
    "unknown": "Нет свежих данных",
}

SYSTEM_META: dict[str, dict[str, Any]] = {
    "thyroid": {
        "purpose_ru": "Контроль щитовидной железы при гипотиреозе / Хашимото. Показывает, подходит ли доза Эутирокса.",
        "purpose_en": "Thyroid control for Hashimoto / hypothyroidism. Shows if Euthyrox dose fits.",
        "tests": ["tsh", "ft4"],
        "meds_ru": ["Эутирокс (левотироксин)"],
        "meds_en": ["Euthyrox (levothyroxine)"],
        "diagnosis_ru": "Гипотиреоз / Хашимото",
        "diagnosis_en": "Hypothyroidism / Hashimoto",
    },
    "pituitary": {
        "purpose_ru": "Контроль гипофиза и пролактиномы. Высокий пролактин может влиять на гормоны, зрение, головные боли.",
        "purpose_en": "Pituitary and prolactinoma control. High prolactin affects hormones, vision, headaches.",
        "tests": ["prolactin"],
        "meds_ru": ["Достинекс (каберголин)"],
        "meds_en": ["Dostinex (cabergoline)"],
        "diagnosis_ru": "Пролактинома",
        "diagnosis_en": "Prolactinoma",
    },
    "menopause": {
        "purpose_ru": "Контроль заместительной гормональной терапии (ЗГТ). Эстрадиол показывает, достаточно ли Дивигеля.",
        "purpose_en": "HRT control. Estradiol shows if Divigel dose is adequate.",
        "tests": ["estradiol"],
        "meds_ru": ["Дивигель (эстрадиол гель)"],
        "meds_en": ["Divigel (estradiol gel)"],
        "diagnosis_ru": "Менопауза",
        "diagnosis_en": "Menopause",
    },
    "blood": {
        "purpose_ru": "Общий статус крови: анемия, обезвоживание, воспаление. Важно при усталости и перед операциями/обследованиями.",
        "purpose_en": "Blood status: anemia, hydration, inflammation. Important when tired or before procedures.",
        "tests": ["hemoglobin", "hematocrit"],
        "meds_ru": [],
        "meds_en": [],
        "diagnosis_ru": "Общеклинический контроль",
        "diagnosis_en": "General blood monitoring",
    },
    "nutrition": {
        "purpose_ru": "Дефициты, которые часто встречаются при менопаузе и гипотиреозе: витамин D, запасы железа (ферритин).",
        "purpose_en": "Common deficits in menopause and hypothyroidism: vitamin D, iron stores (ferritin).",
        "tests": ["vitamin_d", "ferritin"],
        "meds_ru": ["Нутрицевтики (по назначению)"],
        "meds_en": ["Nutraceuticals (as prescribed)"],
        "diagnosis_ru": "Питание / микронутриенты",
        "diagnosis_en": "Nutrition / micronutrients",
    },
}

CHART_META: dict[str, dict[str, str]] = {
    "prolactin": {
        "purpose_ru": "Гормон гипофиза. При пролактиноме контролируется Достинексом.",
        "source_ru": "Таблица lab_results ← фото/PDF анализов через Claude",
    },
    "tsh": {
        "purpose_ru": "Главный показатель функции щитовидной железы на фоне Эутирокса.",
        "source_ru": "Таблица lab_results ← импорт из чата или scripts/import_labs.py",
    },
    "estradiol": {
        "purpose_ru": "Уровень эстрогена. Важен для оценки ЗГТ (Дивигель).",
        "source_ru": "Таблица lab_results ← последний загруженный анализ",
    },
    "vitamin_d": {
        "purpose_ru": "Витамин D: кости, иммунитет, энергия. Ниже 25 нг/мл — дефицит.",
        "source_ru": "Таблица lab_results",
    },
    "hemoglobin": {
        "purpose_ru": "Гемоглобин — перенос кислорода. Низкий → возможная анемия.",
        "source_ru": "Таблица lab_results (ОАК)",
    },
    "sleep_hours": {
        "purpose_ru": "Длительность сна за ночь из Apple Health или Oura.",
        "source_ru": "Таблица daily_metrics ← Health Auto Export или Oura API",
    },
    "resting_hr": {
        "purpose_ru": "Пульс покоя. Отражает восстановление и нагрузку.",
        "source_ru": "Таблица daily_metrics",
    },
    "hrv_sdnn": {
        "purpose_ru": "HRV — вариабельность сердечного ритма, маркер стресса и восстановления.",
        "source_ru": "Таблица daily_metrics (Apple Health / Oura)",
    },
    "steps": {
        "purpose_ru": "Шаги за день — базовая активность.",
        "source_ru": "Таблица daily_metrics",
    },
    "readiness_score": {
        "purpose_ru": "Oura Readiness — готовность организма к нагрузке (0–100).",
        "source_ru": "Oura API → daily_metrics",
    },
}

SECTION_HELP: dict[str, dict[str, str]] = {
    "dashboard": {
        "title_ru": "Дашборд Wellnest",
        "title_en": "Wellnest Dashboard",
        "body_ru": (
            "Это локальная сводка здоровья на вашем Mac. "
            "Цветные карточки сверху — быстрый «светофор» по основным системам. "
            "Данные хранятся в ~/Desktop/HEALTH/data/health.db и обновляются после загрузки анализов через Claude.\n\n"
            "⚠️ Дашборд показывает ФАКТЫ и ИСТОЧНИКИ. "
            "Развёрнутые рекомендации и «почему так» — в чате Claude (проект «Здоровье»)."
        ),
        "body_en": (
            "Local health summary on your Mac. Top cards are traffic lights for key systems. "
            "Data lives in ~/Desktop/HEALTH/data/health.db and updates when labs are imported via Claude.\n\n"
            "⚠️ Dashboard shows FACTS and SOURCES. "
            "Full recommendations and clinical reasoning — in Claude chat («Health» project)."
        ),
        "source_ru": "SQLite health.db + embedded JSON в dashboard.html",
        "source_en": "SQLite health.db + embedded JSON in dashboard.html",
    },
    "today": {
        "title_ru": "Сегодня", "title_en": "Today",
        "body_ru": "Краткие метрики за последний день: сон, пульс, шаги, HRV, готовность Oura. Если пусто — подключите Apple Health или Oura (вкладка «Подключения»).",
        "body_en": "Daily metrics: sleep, HR, steps, HRV, Oura readiness. Empty? Connect Apple Health or Oura.",
        "source_ru": "Таблица daily_metrics, последняя дата",
        "source_en": "daily_metrics table, latest date",
    },
    "charts": {
        "title_ru": "Графики", "title_en": "Charts",
        "body_ru": "Динамика анализов и носимых устройств. Пунктиры — референсный диапазон лаборатории.",
        "body_en": "Lab and wearable trends over time. Dashed lines — lab reference range.",
        "source_ru": "lab_results + daily_metrics",
        "source_en": "lab_results + daily_metrics",
    },
    "labs": {
        "title_ru": "Анализы", "title_en": "Labs",
        "body_ru": "Все сохранённые лабораторные значения. «Свежесть» — можно ли на этом основывать выводы (90–180 дней).",
        "body_en": "All saved lab values. Freshness shows if data is still reliable (90–180 days).",
        "source_ru": "Таблица lab_results; импорт через Claude",
        "source_en": "lab_results table; import via Claude",
    },
    "tasks": {
        "title_ru": "Задачи", "title_en": "Tasks",
        "body_ru": "Открытые пункты: обследования, контрольные анализы, визиты.",
        "body_en": "Open items: imaging, lab rechecks, visits.",
        "source_ru": "Таблица tasks",
        "source_en": "tasks table",
    },
    "meds": {
        "title_ru": "Препараты", "title_en": "Medications",
        "body_ru": "Текущая терапия и назначение. Не меняйте дозы без врача.",
        "body_en": "Current therapy. Do not change doses without your doctor.",
        "source_ru": "medications + profile_context.json",
        "source_en": "medications + profile_context.json",
    },
    "connect": {
        "title_ru": "Подключения", "title_en": "Connections",
        "body_ru": "Apple Health и Oura Ring. Откройте Подключения для настройки синхронизации.",
        "body_en": "Apple Health and Oura Ring. Open Connections to set up sync.",
        "source_ru": "integrations.json + wearables import",
        "source_en": "integrations.json + wearables import",
    },
    "weekly_brief": {
        "title_ru": "На этой неделе", "title_en": "This week",
        "body_ru": "Автоматическая сводка: срочные задачи, отклонения анализов, просроченные контрольные анализы (пролактин, ТТГ, эстрадиол, витамин D).",
        "body_en": "Auto summary: urgent tasks, flagged labs, overdue rechecks (prolactin, TSH, estradiol, vitamin D).",
        "source_ru": "tasks + lab_results + freshness rules",
        "source_en": "tasks + lab_results + freshness rules",
    },
    "checkin": {
        "title_ru": "Вечерний check-in", "title_en": "Evening check-in",
        "body_ru": (
            "Как это работает:\n\n"
            "1. Вечером (после 18:00) Claude сам спросит в чате «Здоровье»: как прошёл день, как спали.\n"
            "2. Вы отвечаете своими словами — цифры ставить не нужно.\n"
            "3. Claude сохраняет и здесь появляются точки за 7 дней.\n\n"
            "Что записывается:\n"
            "• Настроение 1–5 (1 = очень плохо, 5 = отлично)\n"
            "• Сон 1–5 (1 = почти не спала, 5 = выспалась)\n"
            "• Симптомы, если упомянули (головная боль, слабость…)\n\n"
            "Можно и сами написать Claude: «Как прошёл день», «устала», «плохо спала»."
        ),
        "body_en": (
            "How it works:\n\n"
            "1. After 6 PM Claude asks in the Health chat: how was your day, how did you sleep.\n"
            "2. Reply in your own words — no need to pick numbers.\n"
            "3. Claude saves it; dots for the last 7 days appear here.\n\n"
            "What is logged:\n"
            "• Mood 1–5 (1 = very bad, 5 = great)\n"
            "• Sleep 1–5 (1 = barely slept, 5 = well rested)\n"
            "• Symptoms if mentioned (headache, fatigue…)\n\n"
            "You can also tell Claude: «How was my day», «I'm tired», «slept badly»."
        ),
        "source_ru": "Claude (проект «Здоровье») → save_evening_checkin",
        "source_en": "Claude (Health project) → save_evening_checkin",
    },
    "symptom_survey": {
        "title_ru": "Опросник самочувствия", "title_en": "How you feel",
        "body_ru": (
            "Короткий опрос на дашборде: 4 шага, большие кнопки.\n"
            "1) настроение 2) сон 3) симптомы (можно несколько) 4) сохранить.\n"
            "Данные попадают в check-in и видны Claude."
        ),
        "body_en": "Short 4-step survey on dashboard. Saved to check-in.",
        "source_ru": "Дашборд → /api/symptom-survey",
        "source_en": "Dashboard → /api/symptom-survey",
    },
    "consilium": {
        "title_ru": "Консилиум врачей", "title_en": "MDT consilium",
        "body_ru": (
            "6 специалистов + сводка GP. У каждого:\n"
            "🔍 Что вижу · ⚠️ Что настораживает · ✅ Рекомендации · 📎 На основе чего\n\n"
            "Блок «На основе чего» — не black box: анализ (дата, файл), задача, check-in, "
            "гайдлайн со ссылкой (ATA, Endocrine Society, NAMS). «Разбор Claude» — глубокий разбор."
        ),
        "body_en": "MDT with evidence links per specialist.",
        "source_ru": "consilium_format.py + lab_results + reference.db",
        "source_en": "consilium_format.py + lab_results + reference.db",
    },
    "symptom_ask": {
        "title_ru": "Спросите о симптоме", "title_en": "Ask about a symptom",
        "body_ru": (
            "Короткий вопрос на дашборде → Claude отвечает здесь же.\n"
            "Ответ: краткое объяснение + «На основе чего» (анализы, check-in, гайдлайны со ссылками).\n"
            "Не ставит диагноз. После «Спросить» откройте Claude «Здоровье»."
        ),
        "body_en": "Short symptom question → Claude answer with evidence on dashboard.",
        "source_ru": "symptom_qa.py + Claude MCP",
        "source_en": "symptom_qa.py + Claude MCP",
    },
    "claude_analysis": {
        "title_ru": "Где объяснение анализов и рекомендации?",
        "title_en": "Where is analysis explanation?",
        "body_ru": (
            "Разделение ролей:\n\n"
            "📊 ДАШБОРД — факты, опросник, консилиум-структура, «?».\n\n"
            "💬 CLAUDE — живой разбор, рекомендации, развёрнутый консилиум.\n\n"
            "Кнопка «Консилиум» — отчёт по данным. Claude — углублённый разбор."
        ),
        "body_en": (
            "📊 DASHBOARD — facts, survey, consilium structure.\n\n"
            "💬 CLAUDE — live interpretation and deep MDT review."
        ),
        "source_ru": "Claude + MCP wellnest (get_lab_results, get_dashboard_snapshot)",
        "source_en": "Claude + MCP wellnest (get_lab_results, get_dashboard_snapshot)",
    },
}

WEARABLE_LABELS: dict[str, str] = {
    "sleep_hours": "Сон",
    "resting_hr": "Пульс покоя",
    "steps": "Шаги",
    "readiness_score": "Oura Readiness",
    "hrv_sdnn": "HRV",
}


def _format_lab_source(row: dict[str, Any]) -> str:
    src = row.get("source_file") or "импорт через Claude"
    if src and not src.startswith("/"):
        return src
    if src:
        from pathlib import Path
        return Path(src).name
    return "health.db"


def _why_status(status: str, tests: list[str], latest: dict[str, Any]) -> str:
    """Plain-language reason for the traffic-light colour."""
    flags = []
    for code in tests:
        if code not in latest:
            continue
        r = latest[code]
        flag = r.get("flag")
        if flag in ("high", "low"):
            label = TEST_LABELS.get(code, code)
            val = r.get("value") if r.get("value") is not None else r.get("value_text", "—")
            unit = r.get("unit") or ""
            direction = "выше нормы" if flag == "high" else "ниже нормы"
            flags.append(f"{label} {val} {unit} — {direction} (референс лаборатории)")
    if status == "good":
        return (
            "Последние значения по ключевым анализам в референсном диапазоне. "
            "Это не отменяет симптомы — смотрите динамику и назначения врача."
        )
    if status == "caution":
        if flags:
            return f"Одно отклонение: {'; '.join(flags)}. Стоит пересдать в срок и обсудить с врачом, не меняя дозу самостоятельно."
        return "Есть отклонение или устаревшие данные — нужен контроль."
    if status == "warn":
        if flags:
            return f"Несколько отклонений: {'; '.join(flags)}. Приоритет — обсудить с врачом и уточнить план обследований."
        return "Несколько показателей вне нормы — нужен разбор с врачом."
    return "Нет свежих анализов по этой системе — загрузите новый бланк или сдайте контроль."


def _status_reason(status: str, tests: list[str], latest: dict[str, Any]) -> str:
    parts = []
    for code in tests:
        if code not in latest:
            parts.append(f"{TEST_LABELS.get(code, code)}: нет данных")
            continue
        r = latest[code]
        flag = r.get("flag")
        val = r.get("value") if r.get("value") is not None else r.get("value_text", "—")
        unit = r.get("unit") or ""
        date = r.get("sample_date", "—")
        if flag == "high":
            parts.append(f"{TEST_LABELS.get(code, code)} {val} {unit} ↑ ({date})")
        elif flag == "low":
            parts.append(f"{TEST_LABELS.get(code, code)} {val} {unit} ↓ ({date})")
        else:
            parts.append(f"{TEST_LABELS.get(code, code)} {val} {unit} — норма ({date})")
    if not parts:
        return STATUS_LABELS.get(status, status)
    prefix = STATUS_LABELS.get(status, "")
    return f"{prefix}. {'; '.join(parts)}"


def enrich_systems(systems: list[dict[str, Any]], latest: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for s in systems:
        meta = SYSTEM_META.get(s["id"], {})
        tests = meta.get("tests", [])
        sources = []
        for code in tests:
            if code in latest:
                r = latest[code]
                sources.append({
                    "code": code,
                    "test": TEST_LABELS.get(code, code),
                    "value": r.get("value") if r.get("value") is not None else r.get("value_text"),
                    "unit": r.get("unit"),
                    "date": r.get("sample_date"),
                    "flag": r.get("flag"),
                    "file": _format_lab_source(r),
                })
        s = dict(s)
        why_ru = _why_status(s["status"], tests, latest)
        s["explain"] = {
            "purpose_ru": meta.get("purpose_ru", ""),
            "purpose_en": meta.get("purpose_en", meta.get("purpose_ru", "")),
            "diagnosis_ru": meta.get("diagnosis_ru", ""),
            "diagnosis_en": meta.get("diagnosis_en", meta.get("diagnosis_ru", "")),
            "meds_ru": meta.get("meds_ru", []),
            "meds_en": meta.get("meds_en", meta.get("meds_ru", [])),
            "tests_ru": [TEST_LABELS.get(c, c) for c in tests],
            "status_ru": _status_reason(s["status"], tests, latest),
            "status_en": _status_reason(s["status"], tests, latest),
            "why_ru": why_ru,
            "why_en": why_ru,
            "sources": sources,
            "chart_codes": tests,
            "data_from_ru": "SQLite ~/Desktop/HEALTH/data/health.db → таблица lab_results",
            "data_from_en": "SQLite ~/Desktop/HEALTH/data/health.db → lab_results table",
        }
        out.append(s)
    return out


def enrich_charts(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("lab_charts", "wearable_charts"):
        enriched = []
        for c in payload.get(key, []):
            code = c.get("code", "")
            meta = CHART_META.get(code, {})
            item = dict(c)
            item["explain"] = {
                "purpose_ru": meta.get("purpose_ru", ""),
                "source_ru": meta.get("source_ru", "health.db"),
                "latest_ru": f"Последнее: {c.get('latest', '—')} {c.get('unit', '')} ({c.get('latest_date') or '—'})"
                if key == "lab_charts"
                else f"Последнее: {c.get('latest', '—')} {c.get('unit', '')} · источник: {c.get('source', '—')}",
            }
            enriched.append(item)
        payload[key] = enriched
    payload["systems"] = payload.get("systems", [])
    return payload


def help_sections() -> dict[str, dict[str, str]]:
    return SECTION_HELP


def today_metric_help(code: str, row: dict[str, Any] | None) -> dict[str, str]:
    label = WEARABLE_LABELS.get(code, code)
    meta = CHART_META.get(code, {})
    val = "—"
    src = "—"
    dt = "—"
    if row:
        val = str(row.get("value", "—"))
        src = row.get("source", "—")
        dt = row.get("metric_date", "—")
    return {
        "title": label,
        "body_ru": meta.get("purpose_ru", f"Метрика {label}"),
        "source_ru": f"{meta.get('source_ru', 'daily_metrics')} · {val} · {dt} · {src}",
    }
