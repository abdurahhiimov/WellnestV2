"""Prepare chart series for dashboard."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend import health_db
from backend.wearables import get_daily_metrics

# Lab chart definitions
LAB_CHARTS = [
    {"code": "prolactin", "title": "Пролактин", "unit": "мМЕ/л", "ref_low": 40, "ref_high": 550, "color": "#2dd4bf"},
    {"code": "tsh", "title": "ТТГ", "unit": "мМЕ/л", "ref_low": 0.3, "ref_high": 4.0, "color": "#60a5fa"},
    {"code": "ft4", "title": "Т4 свободный", "unit": "пмоль/л", "ref_low": 9.0, "ref_high": 22.2, "color": "#93c5fd"},
    {"code": "estradiol", "title": "Эстрадиол", "unit": "нмоль/л", "ref_low": 0.0, "ref_high": 0.23, "color": "#f472b6"},
    {"code": "vitamin_d", "title": "Витамин D", "unit": "нг/мл", "ref_low": 25, "ref_high": 80, "color": "#fbbf24"},
    {"code": "ferritin", "title": "Ферритин", "unit": "нг/мл", "ref_low": 10, "ref_high": 150, "color": "#a3e635"},
    {"code": "hemoglobin", "title": "Гемоглобин", "unit": "г/л", "ref_low": 120, "ref_high": 140, "color": "#f87171"},
    {"code": "hematocrit", "title": "Гематокрит", "unit": "%", "ref_low": 36, "ref_high": 50, "color": "#e879f9"},
]

WEARABLE_CHARTS = [
    {"code": "sleep_hours", "title": "Сон", "unit": "ч", "color": "#818cf8"},
    {"code": "resting_hr", "title": "Пульс покоя", "unit": "уд/мин", "color": "#fb7185"},
    {"code": "hrv_sdnn", "title": "HRV", "unit": "ms", "color": "#34d399"},
    {"code": "steps", "title": "Шаги", "unit": "", "color": "#38bdf8"},
    {"code": "readiness_score", "title": "Oura Readiness", "unit": "", "color": "#a78bfa"},
]


def _lab_benchmark(latest_row: dict, profile_id: str | None = None) -> dict[str, Any]:
    """Build benchmark bands: lab reference + diagnosis-specific clinical target."""
    from backend import health_db
    from backend.reference_db import compare_lab_to_reference, lookup_lab_reference

    code = latest_row.get("test_code") or ""
    value = latest_row.get("value")
    compare = compare_lab_to_reference(latest_row)
    ref = lookup_lab_reference(test_code=code)

    profile = health_db.get_patient_profile(profile_id)
    dx = {d.get("code") for d in profile.get("diagnoses", []) if isinstance(d, dict)}

    bench: dict[str, Any] = {
        "patient_value": value,
        "unit": latest_row.get("unit") or "",
        "date": latest_row.get("sample_date"),
        "flag": latest_row.get("flag"),
        "lab_ref": {
            "low": latest_row.get("ref_low"),
            "high": latest_row.get("ref_high"),
            "label_ru": "Референс лаборатории",
            "label_en": "Lab reference range",
        },
        "notes_ru": compare.get("notes_ru") or [],
        "clinical_band_ru": compare.get("clinical_band_ru"),
        "sources": compare.get("reference_sources") or [],
        "interpretation_ru": (ref or {}).get("interpretation_ru"),
    }

    if not ref or value is None:
        return bench

    if "hashimoto" in dx and ref.get("therapeutic_target_hashimoto"):
        t = ref["therapeutic_target_hashimoto"]
        bench["clinical_target"] = {
            "low": t.get("low"),
            "high": t.get("high"),
            "label_ru": "Цель при Hashimoto (частая практика)",
            "label_en": "Hashimoto therapeutic target",
            "note_ru": t.get("note_ru"),
        }
    if "prolactinoma" in dx and ref.get("therapeutic_target_prolactinoma"):
        t = ref["therapeutic_target_prolactinoma"]
        bench["clinical_target"] = {
            "low": latest_row.get("ref_low"),
            "high": latest_row.get("ref_high"),
            "label_ru": "Контроль пролактиномы (динамика на Достинексе)",
            "label_en": "Prolactinoma control range",
            "note_ru": t.get("note_ru"),
        }
    if "menopause" in dx and ref.get("therapeutic_target_hrt") and code == "estradiol":
        t = ref["therapeutic_target_hrt"]
        bench["clinical_target"] = {
            "low": latest_row.get("ref_low"),
            "high": latest_row.get("ref_high"),
            "label_ru": "ЗГТ — индивидуальный диапазон (NAMS)",
            "label_en": "HRT individual range",
            "note_ru": t.get("note_ru"),
        }
    if ref.get("clinical_bands"):
        bench["clinical_bands"] = ref["clinical_bands"]

    return bench


def _lab_series(profile_id: str | None = None) -> list[dict[str, Any]]:
    labs = health_db.get_lab_results(limit=200, profile_id=profile_id)
    by_code: dict[str, list] = defaultdict(list)
    for lab in labs:
        by_code[lab["test_code"]].append(lab)

    charts = []
    seen: set[str] = set()
    for spec in LAB_CHARTS:
        rows = sorted(by_code.get(spec["code"], []), key=lambda x: x["sample_date"])
        # One point per date (latest id wins)
        by_date: dict[str, Any] = {}
        for r in rows:
            by_date[r["sample_date"]] = r
        rows = [by_date[d] for d in sorted(by_date.keys())]
        if not rows:
            continue
        seen.add(spec["code"])
        latest = rows[-1]
        charts.append({
            **spec,
            "labels": [r["sample_date"] for r in rows],
            "values": [r["value"] for r in rows],
            "flags": [r.get("flag") for r in rows],
            "latest": latest.get("value"),
            "latest_flag": latest.get("flag"),
            "latest_date": latest.get("sample_date"),
            "benchmark": _lab_benchmark(latest, profile_id),
        })

    # Any other tests in DB (e.g. from imports) — grey default color
    for code, raw_rows in sorted(by_code.items()):
        if code in seen:
            continue
        rows = sorted(raw_rows, key=lambda x: x["sample_date"])
        by_date = {r["sample_date"]: r for r in rows}
        rows = [by_date[d] for d in sorted(by_date.keys())]
        if not rows:
            continue
        latest = rows[-1]
        charts.append({
            "code": code,
            "title": latest.get("test_name_ru") or code,
            "unit": latest.get("unit") or "",
            "ref_low": latest.get("ref_low"),
            "ref_high": latest.get("ref_high"),
            "color": "#94a3b8",
            "labels": [r["sample_date"] for r in rows],
            "values": [r["value"] for r in rows],
            "flags": [r.get("flag") for r in rows],
            "latest": latest.get("value"),
            "latest_flag": latest.get("flag"),
            "latest_date": latest.get("sample_date"),
            "benchmark": _lab_benchmark(latest, profile_id),
        })
    return charts


def _wearable_series(profile_id: str | None = None) -> list[dict[str, Any]]:
    charts = []
    for spec in WEARABLE_CHARTS:
        rows = get_daily_metrics(spec["code"], days=60, profile_id=profile_id)
        if not rows:
            continue
        charts.append({
            **spec,
            "labels": [r["metric_date"] for r in rows],
            "values": [r["value"] for r in rows],
            "latest": rows[-1]["value"],
            "source": rows[-1]["source"],
        })
    return charts


def system_status(profile_id: str | None = None) -> list[dict[str, Any]]:
    """Traffic-light cards per clinical system."""
    labs = {r["test_code"]: r for r in health_db.get_lab_results(limit=50, profile_id=profile_id)}
    # dedupe by test_code keeping latest date
    latest: dict[str, Any] = {}
    for r in health_db.get_lab_results(limit=200, profile_id=profile_id):
        if r["test_code"] not in latest or r["sample_date"] >= latest[r["test_code"]]["sample_date"]:
            latest[r["test_code"]] = r

    def status_for(codes: list[str]) -> str:
        flags = [latest[c]["flag"] for c in codes if c in latest and latest[c].get("flag")]
        if not flags:
            return "unknown"
        if any(f in ("high", "low") for f in flags):
            if sum(1 for f in flags if f in ("high", "low")) >= 2:
                return "warn"
            return "caution"
        return "good"

    return _systems_for_profile(profile_id, status_for)


# Body-system catalog. A system shows on the dashboard when the user has a
# matching condition (by code) OR has labs for it. `always` ones are general
# wellness systems shown to everyone.
_SYSTEM_CATALOG = [
    {"id": "thyroid", "title": "Щитовидная", "title_en": "Thyroid", "icon": "/icons/thyroid.png",
     "labs": ["tsh", "ft4", "t4", "t3"], "conditions": ["hypothyroidism", "hashimoto", "hyperthyroidism", "thyroid_nodule"]},
    {"id": "pituitary", "title": "Гипофиз", "title_en": "Pituitary", "icon": "🧠",
     "labs": ["prolactin"], "conditions": ["prolactinoma", "pituitary"]},
    {"id": "menopause", "title": "Менопауза / ЗГТ", "title_en": "Menopause / HRT", "icon": "/icons/menopause.png",
     "labs": ["estradiol", "fsh", "lh"], "conditions": ["menopause", "perimenopause"]},
    {"id": "metabolic", "title": "Обмен веществ", "title_en": "Metabolic", "icon": "🍬",
     "labs": ["glucose", "hba1c", "insulin"], "conditions": ["diabetes", "prediabetes", "obesity"]},
    {"id": "heart", "title": "Сердце", "title_en": "Heart", "icon": "❤️",
     "labs": ["cholesterol", "ldl", "hdl", "triglycerides"], "conditions": ["hypertension", "high_cholesterol", "heart_disease", "arrhythmia"]},
    {"id": "bones", "title": "Кости и суставы", "title_en": "Bones & joints", "icon": "🦴",
     "labs": ["calcium", "vitamin_d"], "conditions": ["osteoporosis", "osteopenia", "arthritis", "joint_pain"]},
    {"id": "blood", "title": "Кровь", "title_en": "Blood", "icon": "🩸",
     "labs": ["hemoglobin", "hematocrit", "ferritin"], "conditions": ["anemia"], "always": True},
    {"id": "nutrition", "title": "Питание", "title_en": "Nutrition", "icon": "/icons/nutrition.png",
     "labs": ["vitamin_d", "ferritin", "b12"], "conditions": ["vitamin_deficiency"], "always": True},
]


def _systems_for_profile(profile_id, status_for):
    from backend.profile_store import load_profile

    profile = load_profile(profile_id)
    codes = {str(c.get("code", "")).lower() for c in (profile.get("conditions") or [])}

    out = []
    for s in _SYSTEM_CATALOG:
        relevant = s.get("always") or bool(codes & set(s["conditions"]))
        if relevant:
            out.append({
                "id": s["id"], "title": s["title"], "title_en": s["title_en"],
                "status": status_for(s["labs"]), "icon": s["icon"],
            })
    # Cap at 5 cards; ensure at least the general ones show.
    return out[:5]


def chart_payload(profile_id: str | None = None) -> dict[str, Any]:
    from backend.explainability import enrich_charts, enrich_systems

    labs = health_db.get_lab_results(limit=200, profile_id=profile_id)
    latest: dict[str, Any] = {}
    for r in labs:
        if r["test_code"] not in latest or r["sample_date"] >= latest[r["test_code"]]["sample_date"]:
            latest[r["test_code"]] = r

    systems = enrich_systems(system_status(profile_id), latest)
    payload = {
        "lab_charts": _lab_series(profile_id),
        "wearable_charts": _wearable_series(profile_id),
        "systems": systems,
    }
    return enrich_charts(payload)
