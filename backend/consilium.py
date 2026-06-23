"""MDT consilium — structured opinion per specialist (4 sections each)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from backend import health_db
from backend.checkins import get_checkins
from backend.explainability import TEST_LABELS
from backend.paths import ensure_health_folders
from backend.weekly_brief import build_weekly_brief

# Opinion keys (RU labels for HTML)
SECTION_LABELS = {
    "see": "Что вижу",
    "concerns": "Что настораживает",
    "recommendations": "Рекомендации",
    "reasoning": "Почему я так считаю (на основе чего)",
}

SPECIALIST_ROLES = [
    ("endo", "Эндокринолог", "Endocrinologist", "Щитовидная, гипофиз, гормоны"),
    ("gyn", "Гинеколог", "Gynecologist", "Менопауза, ЗГТ"),
    ("neuro", "Невролог", "Neurologist", "Головные боли, пролактинома, сон"),
    ("nutri", "Нутрициолог", "Nutritionist", "Витамины, железо, кровь"),
    ("ortho", "Ортопед", "Orthopedist", "Суставы, плечо, нагрузка"),
    ("gp", "Семейный врач (сводка)", "GP chair", "Общая координация"),
]


from backend.consilium_format import (
    render_consilium_body_html,
    render_specialist_card_html,
)


def _esc(s: Any) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _blank_opinion() -> dict[str, Any]:
    return {"see": [], "concerns": [], "recommendations": [], "reasoning": [], "evidence": []}


def _lab_evidence(s: dict[str, Any] | None) -> dict[str, Any] | None:
    if not s:
        return None
    return {
        "claim_ru": f"{s['name']}: {s['value']} {s['unit']}".strip(),
        "kind": "lab",
        "ref": s.get("code"),
        "date": s.get("date"),
        "value": s.get("value"),
        "unit": s.get("unit"),
        "source_label": s.get("source") or "health.db → lab_results",
    }


def _attach_lab_evidence(op: dict[str, Any], snap: dict[str, Any] | None) -> None:
    ev = _lab_evidence(snap)
    if ev:
        op.setdefault("evidence", []).append(ev)


def _latest_labs_by_code(labs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in labs:
        code = row.get("test_code")
        if code and code not in out:
            out[code] = row
    return out


def _lab_snapshot(code: str, latest: dict[str, dict]) -> dict[str, Any] | None:
    r = latest.get(code)
    if not r:
        return None
    val = r.get("value") if r.get("value") is not None else r.get("value_text", "—")
    return {
        "code": code,
        "name": TEST_LABELS.get(code, code),
        "value": val,
        "unit": r.get("unit") or "",
        "flag": r.get("flag"),
        "date": r.get("sample_date", "—"),
        "freshness": r.get("freshness") or {},
        "source": r.get("source_file") or "lab_results / health.db",
    }


def _fmt_lab(s: dict[str, Any] | None) -> str:
    if not s:
        return ""
    arrow = " ↑" if s["flag"] == "high" else " ↓" if s["flag"] == "low" else ""
    return f"{s['name']}: {s['value']} {s['unit']}{arrow} от {s['date']}"


def _evidence(s: dict[str, Any] | None) -> str:
    if not s:
        return ""
    fresh = s["freshness"].get("message_ru", "")
    src = s["source"]
    if len(str(src)) > 60:
        src = "импорт анализов"
    parts = [f"Анализ {s['name']} ({s['date']})", f"значение {s['value']} {s['unit']}".strip()]
    if s["flag"]:
        parts.append("отклонение от референса")
    if fresh:
        parts.append(fresh)
    parts.append(f"источник: {src}")
    return "; ".join(parts)


def _tasks_by_keyword(tasks: list[dict], *keywords: str) -> list[str]:
    out = []
    for t in tasks:
        title = (t.get("title_ru") or "").lower()
        if any(k in title for k in keywords):
            out.append(t["title_ru"])
    return out


def _recent_checkin_symptoms(profile_id: str | None) -> list[str]:
    symptoms: list[str] = []
    for row in get_checkins(days=14, profile_id=profile_id)[:7]:
        p = row.get("payload") or {}
        for s in p.get("symptoms") or []:
            if s and s not in symptoms:
                symptoms.append(s)
    return symptoms


def _add(op: dict[str, list[str]], section: str, line: str) -> None:
    if line and line not in op[section]:
        op[section].append(line)


def _build_endo(latest: dict, meds: list[dict], tasks: list[dict]) -> dict[str, list[str]]:
    op = _blank_opinion()
    tsh = _lab_snapshot("tsh", latest)
    prl = _lab_snapshot("prolactin", latest)
    e2 = _lab_snapshot("estradiol", latest)
    ft4 = _lab_snapshot("ft4", latest)

    med_map = {m.get("purpose", ""): m["name"] for m in meds}
    _add(op, "see", f"Терапия: {med_map.get('hypothyroidism', 'Эутирокс')}, "
                     f"{med_map.get('prolactinoma', 'Достинекс')}, "
                     f"{med_map.get('HRT / menopause', 'Дивигель')}.")
    for snap in (tsh, prl, e2, ft4):
        if snap:
            _add(op, "see", _fmt_lab(snap))

    for snap, label in ((tsh, "ТТГ"), (prl, "пролактин"), (e2, "эстрадиол")):
        if not snap:
            _add(op, "concerns", f"Нет данных по {label} — сложно оценить баланс терапии.")
            continue
        if snap["flag"] in ("low", "high"):
            _add(op, "concerns", f"{label} вне референса ({snap['value']} {snap['unit']}, {snap['date']}).")
        if snap["freshness"].get("status") in ("aging", "stale"):
            _add(op, "concerns", f"{label}: {snap['freshness'].get('message_ru', 'данные устарели')}.")

    _add(op, "recommendations", "Обсудить с эндокринологом согласованность Эутирокса, Достинекса и Дивигеля по последним анализам.")
    if any(_tasks_by_keyword(tasks, "мрт", "гипофиз")):
        _add(op, "recommendations", "Запланировать/обсудить МРТ гипофиза из списка задач.")
    _add(op, "recommendations", "Контроль ТТГ, пролактина и эстрадиола по графику врача.")

    for snap in (tsh, prl, e2):
        _attach_lab_evidence(op, snap)

    if not op.get("evidence") and not op["reasoning"]:
        _add(op, "reasoning", "Выводы основаны на профиле диагнозов и таблице lab_results.")
    return op


def _build_gyn(latest: dict, tasks: list[dict], symptoms: list[str]) -> dict[str, list[str]]:
    op = _blank_opinion()
    e2 = _lab_snapshot("estradiol", latest)
    _add(op, "see", "Менопауза, заместительная гормональная терапия (Дивигель).")
    if e2:
        _add(op, "see", _fmt_lab(e2))
    meno_sym = [s for s in symptoms if any(k in s.lower() for k in ("прилив", "сухость", "меноп"))]
    if meno_sym:
        _add(op, "see", f"Из check-in: {', '.join(meno_sym[:3])}.")

    if e2 and e2["flag"] == "high":
        _add(op, "concerns", "Эстрадиол выше референса — оценить дозу ЗГТ.")
    elif e2 and e2["flag"] == "low":
        _add(op, "concerns", "Эстрадиол ниже референса — симптомы менопаузы могут сохраняться.")
    if _tasks_by_keyword(tasks, "узи", "малого таза", "таза"):
        _add(op, "concerns", "УЗИ малого таза в открытых задачах — не откладывать без причины.")

    _add(op, "recommendations", "Обсудить эффективность и безопасность ЗГТ на ближайшем приёме.")
    _add(op, "recommendations", "Контроль эстрадиола по назначению гинеколога/эндокринолога.")
    if _tasks_by_keyword(tasks, "узи", "таз"):
        _add(op, "recommendations", "Выполнить УЗИ малого таза из списка задач.")

    if e2:
        _attach_lab_evidence(op, e2)
    op.setdefault("evidence", []).append(
        {"claim_ru": "Диагноз менопауза; ЗГТ — Дивигель", "kind": "profile", "source_label": "profile_context.json"}
    )
    return op


def _build_neuro(latest: dict, tasks: list[dict], symptoms: list[str]) -> dict[str, list[str]]:
    op = _blank_opinion()
    prl = _lab_snapshot("prolactin", latest)
    _add(op, "see", "Пролактинома (микроаденома гипофиза) в активных диагнозах.")
    if prl:
        _add(op, "see", _fmt_lab(prl))

    head = [s for s in symptoms if "голов" in s.lower() or "головокруж" in s.lower()]
    if head:
        _add(op, "see", f"Жалобы из опросника/check-in: {', '.join(head)}.")
    checkins = get_checkins(days=7)
    if checkins:
        avg_mood = []
        for c in checkins:
            p = c.get("payload") or {}
            if p.get("mood"):
                avg_mood.append(int(p["mood"]))
        if avg_mood:
            _add(op, "see", f"Среднее настроение за неделю (check-in): {sum(avg_mood)/len(avg_mood):.1f}/5.")

    if prl and prl["flag"] == "high":
        _add(op, "concerns", "Повышенный пролактин — контроль симптомов со стороны гипофиза.")
    if head:
        _add(op, "concerns", "Головная боль/головокружение — исключить связь с пролактиномой; при нарастании — срочно к врачу.")
    _add(op, "concerns", "При нарушении зрения, сильной головной боли — не ждать планового визита.")

    _add(op, "recommendations", "Обсудить головные боли и сон с неврологом/эндокринологом.")
    _add(op, "recommendations", "Продолжать контроль пролактина на фоне Достинекса.")
    if _tasks_by_keyword(tasks, "мрт", "гипофиз"):
        _add(op, "recommendations", "МРТ гипофиза — по задаче и согласованию с врачом.")

    if prl:
        _add(op, "reasoning", _evidence(prl))
    if head:
        _add(op, "reasoning", "Симптомы зафиксированы в таблице checkins (опросник или Claude).")
    return op


def _build_nutri(latest: dict, tasks: list[dict]) -> dict[str, list[str]]:
    op = _blank_opinion()
    vd = _lab_snapshot("vitamin_d", latest)
    ferr = _lab_snapshot("ferritin", latest)
    hb = _lab_snapshot("hemoglobin", latest)

    for snap in (vd, ferr, hb):
        if snap:
            _add(op, "see", _fmt_lab(snap))

    for snap, name in ((vd, "Витамин D"), (ferr, "Ферритин"), (hb, "Гемоглобин")):
        if not snap:
            continue
        if snap["flag"] == "low":
            _add(op, "concerns", f"{name} ниже референса — возможен дефицит/анемия, влияет на энергию.")
        if snap["freshness"].get("status") in ("aging", "stale"):
            _add(op, "concerns", f"{name}: актуальность данных — {snap['freshness'].get('message_ru', 'устарело')}.")

    _add(op, "recommendations", "Обсудить коррекцию витамина D и железа с врачом (не менять дозы самостоятельно).")
    _add(op, "recommendations", "Питание и нутрицевтики — только по текущей схеме врача.")

    for snap in (vd, ferr, hb):
        ev = _evidence(snap)
        if ev:
            _add(op, "reasoning", ev)
    return op


def _build_ortho(tasks: list[dict], symptoms: list[str]) -> dict[str, list[str]]:
    op = _blank_opinion()
    shoulder = [s for s in symptoms if "плеч" in s.lower() or "сустав" in s.lower()]
    shoulder_tasks = _tasks_by_keyword(tasks, "плеч", "узи плеч")

    if shoulder_tasks:
        _add(op, "see", f"Открытые задачи: {', '.join(shoulder_tasks)}.")
    if shoulder:
        _add(op, "see", f"Жалобы: {', '.join(shoulder)}.")
    if not shoulder and not shoulder_tasks:
        _add(op, "see", "Явных ортопедических жалоб в последних check-in не отмечено.")

    if shoulder:
        _add(op, "concerns", "Боль в плече — ограничивает активность; нужна очная оценка.")
    if shoulder_tasks:
        _add(op, "concerns", "УЗИ/обследование плеча в списке задач — без диагностики сложно планировать лечение.")

    _add(op, "recommendations", "Выполнить УЗИ плеча и показать результат лечащему врачу.")
    _add(op, "recommendations", "Избегать перегрузки поражённого плеча до очной консультации.")

    if shoulder:
        _add(op, "reasoning", "Симптом «боль в плече» из опросника/check-in на дашборде.")
    if shoulder_tasks:
        _add(op, "reasoning", "Задача в таблице tasks (Wellnest).")
    return op


def _build_gp(brief: dict, tasks: list[dict], specialists: list[dict]) -> dict[str, list[str]]:
    op = _blank_opinion()
    for item in brief.get("items", [])[:5]:
        _add(op, "see", item["text_ru"])

    urgent = [t for t in tasks if t["priority"] == "urgent"]
    for t in urgent:
        _add(op, "concerns", f"Срочно: {t['title_ru']}")

    flagged = sum(1 for sp in specialists if sp.get("opinion", {}).get("concerns"))
    if flagged:
        _add(op, "concerns", f"У {flagged} специалистов консилиума есть пункты «настораживает» — см. разделы выше.")

    _add(op, "recommendations", "Приоритет: срочные задачи и отклонения анализов — обсудить с лечащими врачами.")
    _add(op, "recommendations", "Для развёрнутого разбора — Claude «Здоровье» (живой консилиум).")
    _add(op, "recommendations", brief.get("headline_ru", ""))

    _add(op, "reasoning", "Сводка построена из weekly_brief, tasks, lab_results и checkins (локальная база health.db).")
    _add(op, "reasoning", f"Дата формирования: {datetime.now().strftime('%Y-%m-%d %H:%M')}.")
    return op


def _builders() -> dict[str, Any]:
    return {
        "endo": _build_endo,
        "gyn": _build_gyn,
        "neuro": _build_neuro,
        "nutri": _build_nutri,
        "ortho": _build_ortho,
    }


def build_consilium_sections(profile_id: str | None = None) -> dict[str, Any]:
    profile = health_db.get_patient_profile(profile_id)
    labs = health_db.get_lab_results(limit=40, profile_id=profile_id)
    latest = _latest_labs_by_code(labs)
    brief = build_weekly_brief(profile_id)
    meds = health_db.get_medications(profile_id)
    tasks = health_db.get_tasks(profile_id)
    symptoms = _recent_checkin_symptoms(profile_id)

    builders = _builders()
    specialists: list[dict[str, Any]] = []

    for sid, title_ru, title_en, focus in SPECIALIST_ROLES[:-1]:
        fn = builders[sid]
        if sid == "ortho":
            opinion = fn(tasks, symptoms)
        elif sid == "gyn":
            opinion = fn(latest, tasks, symptoms)
        elif sid == "neuro":
            opinion = fn(latest, tasks, symptoms)
        elif sid == "nutri":
            opinion = fn(latest, tasks)
        else:
            opinion = fn(latest, meds, tasks)
        specialists.append({
            "id": sid,
            "title_ru": title_ru,
            "title_en": title_en,
            "focus_ru": focus,
            "opinion": opinion,
        })

    gp_opinion = _build_gp(brief, tasks, specialists)
    specialists.append({
        "id": "gp",
        "title_ru": SPECIALIST_ROLES[-1][1],
        "title_en": SPECIALIST_ROLES[-1][2],
        "focus_ru": SPECIALIST_ROLES[-1][3],
        "opinion": gp_opinion,
    })

    claude_prompt = (
        "Сделай развёрнутый консилиум по моим данным Wellnest. "
        "Для каждого врача (эндокринолог, гинеколог, невролог, нутрициолог, ортопед): "
        "что вижу, что настораживает, рекомендации, почему так считаю — с опорой на мои анализы."
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "patient": profile.get("display_name"),
        "medications_summary": ", ".join(m["name"] for m in meds[:8]),
        "headline_ru": brief.get("headline_ru", ""),
        "section_labels": SECTION_LABELS,
        "specialists": specialists,
        "claude_prompt_ru": claude_prompt,
        "claude_prompt_en": (
            "Detailed MDT consilium from my Wellnest data. "
            "Per doctor: what I see, concerns, recommendations, reasoning from my labs."
        ),
    }


def _opinion_block(title: str, focus: str, opinion: dict[str, Any], labels: dict[str, str], spec_id: str = "") -> str:
    sid = spec_id
    if not sid:
        for role_id, title_ru, _, _ in SPECIALIST_ROLES:
            if title_ru in title or title.startswith(title_ru.split()[0]):
                sid = role_id
                break
    return render_specialist_card_html(
        {"id": sid, "title_ru": title, "focus_ru": focus, "opinion": opinion},
        lang="ru",
    )


def build_consilium_html_from_data(
    data: dict[str, Any],
    *,
    footer_note: str | None = None,
    show_claude_prompt: bool = False,
) -> str:
    generated = (data.get("generated_at") or "")[:16].replace("T", " ")
    labels = data.get("section_labels") or SECTION_LABELS
    source = data.get("source", "rules")
    source_label = "Claude (локально)" if source == "claude" else "локальные данные (анализы, задачи, check-in)"
    specs_html = ""
    for sp in data.get("specialists", []):
        specs_html += _opinion_block(
            sp.get("title_ru", ""),
            sp.get("focus_ru", ""),
            sp.get("opinion") or {},
            labels,
            spec_id=sp.get("id") or "",
        )
    prompt_block = ""
    if show_claude_prompt and data.get("claude_prompt_ru"):
        prompt_block = f"""
  <div class="claude noprint">
    <strong>Развёрнутый консилиум в Claude</strong>
    <p>Для живого разбора откройте Claude «Здоровье»:</p>
    <code>{_esc(data['claude_prompt_ru'])}</code>
  </div>"""
    footer = f"<p class='meta noprint'>{_esc(footer_note)}</p>" if footer_note else ""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Консилиум — {_esc(data.get('patient'))}</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 920px; margin: 2rem auto; padding: 0 1rem; color: #111; line-height: 1.55; }}
    h1 {{ font-size: 1.35rem; }}
    .meta {{ color: #555; font-size: 0.875rem; margin-bottom: 1.25rem; }}
    .spec-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1.1rem 1.2rem; margin-bottom: 1.1rem; }}
    .spec-card.spec-gp {{ background: #eff6ff; border-color: #bfdbfe; }}
    .spec-head {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.65rem; }}
    .spec-emoji {{ font-size: 1.35rem; }}
    .spec-title {{ margin: 0; font-size: 1.1rem; color: #0f766e; }}
    .spec-focus {{ margin: 0 0 0.75rem; font-size: 0.8125rem; color: #64748b; }}
    .spec-sec {{ margin-bottom: 0.85rem; }}
    .spec-sec h5 {{ margin: 0 0 0.35rem; font-size: 0.8125rem; font-weight: 700; color: #334155; }}
    .spec-p {{ margin: 0 0 0.45rem; font-size: 0.9375rem; color: #1e293b; }}
    .spec-sec ul {{ margin: 0.25rem 0 0; padding-left: 1.2rem; font-size: 0.9375rem; }}
    .spec-sec li {{ margin-bottom: 0.35rem; }}
    .ev-list {{ list-style: none; padding: 0; margin: 0.35rem 0 0; }}
    .ev-item {{ font-size: 0.8125rem; padding: 0.45rem 0.55rem; margin-bottom: 0.35rem; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }}
    .ev-kind {{ display: inline-block; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; color: #0f766e; margin-right: 0.35rem; }}
    .ev-meta {{ display: block; color: #64748b; margin-top: 0.2rem; font-size: 0.75rem; }}
    .ev-item a {{ color: #2563eb; }}
    .legend {{ font-size: 0.8125rem; color: #64748b; margin-bottom: 1rem; padding: 0.65rem 0.85rem; background: #f1f5f9; border-radius: 8px; }}
    .claude {{ background: #fef3c7; border: 1px solid #fcd34d; border-radius: 12px; padding: 1rem; margin-top: 1.25rem; font-size: 0.875rem; }}
    .claude code {{ display: block; margin-top: 0.5rem; padding: 0.65rem; background: #fff; border-radius: 8px; white-space: pre-wrap; }}
    @media print {{ .noprint {{ display: none; }} }}
  </style>
</head>
<body>
  <p class="noprint"><a href="/dashboard">← Дашборд</a> · Cmd+P → PDF</p>
  <h1>Консилиум врачей — {_esc(data.get('patient'))}</h1>
  <p class="meta">Сформировано: {generated} · {source_label}</p>
  {footer}
  <p class="legend">У каждого специалиста: <strong>что вижу</strong> · <strong>что настораживает</strong> · <strong>рекомендации</strong> · <strong>на основе чего</strong></p>
  <p><strong>На этой неделе:</strong> {_esc(data.get('headline_ru'))}</p>
  <p><strong>Препараты:</strong> {_esc(data.get('medications_summary'))}</p>
  {specs_html}
  {prompt_block}
</body>
</html>"""


def build_consilium_html(profile_id: str | None = None) -> str:
    data = build_consilium_sections(profile_id)
    return build_consilium_html_from_data(data, show_claude_prompt=True)


def export_consilium(profile_id: str | None = None) -> Path:
    root = ensure_health_folders(profile_id)
    path = root / "reports" / "consilium_latest.html"
    path.write_text(build_consilium_html(profile_id), encoding="utf-8")
    return path
