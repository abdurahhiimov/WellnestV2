"""Printable doctor visit pack (HTML → Print to PDF in Safari)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from backend import health_db
from backend.paths import ensure_health_folders
from backend.report_locale import (
    VISIT_PACK,
    category_label,
    diagnosis_label,
    flag_label,
    normalize_lang,
    priority_label,
    purpose_label,
    test_name,
)
from backend.weekly_brief import build_weekly_brief


def _esc(s: Any) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Section ids the report can include, in render order. None => DEFAULT_SECTIONS.
ALL_SECTIONS = [
    "diagnoses", "week", "allergies", "meds", "labs",
    "immunizations", "procedures", "family_history", "tasks", "questions",
]
DEFAULT_SECTIONS = ["diagnoses", "week", "allergies", "meds", "labs", "tasks", "questions"]

# Bilingual labels for the sections MediKeep added (kept local to avoid touching
# report_locale for every new field).
_SEC_LABELS = {
    "allergies": {"ru": "Аллергии", "en": "Allergies"},
    "immunizations": {"ru": "Прививки", "en": "Immunizations"},
    "procedures": {"ru": "Процедуры и операции", "en": "Procedures"},
    "family_history": {"ru": "Семейный анамнез", "en": "Family history"},
}


def build_visit_pack_html(profile_id: str | None = None, lang: str = "ru",
                          sections: list[str] | None = None) -> str:
    from backend.profile_store import load_profile

    lang = normalize_lang(lang)
    L = VISIT_PACK[lang]
    picked = [s for s in (sections or DEFAULT_SECTIONS) if s in ALL_SECTIONS]
    profile = health_db.get_patient_profile(profile_id)
    user_profile = load_profile(profile_id)
    meds = health_db.get_medications(profile_id)
    tasks = health_db.get_active_tasks(profile_id)
    labs = health_db.get_lab_results(limit=30, profile_id=profile_id)
    brief = build_weekly_brief(profile_id)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _sec_label(key: str) -> str:
        return _SEC_LABELS[key][lang]

    diag_lines = "".join(
        f"<li>{_esc(diagnosis_label(d, lang))}</li>"
        for d in profile.get("diagnoses", [])
    )
    med_rows = "".join(
        f"<tr><td>{_esc(m['name'])}</td><td>{_esc(m.get('dose') or '—')}</td>"
        f"<td>{_esc(purpose_label(m.get('purpose'), lang))}</td></tr>"
        for m in meds
    )
    task_rows = "".join(
        f"<tr><td>{_esc(t['title_ru'])}</td><td>{_esc(priority_label(t['priority'], lang))}</td>"
        f"<td>{_esc(category_label(t.get('category'), lang))}</td></tr>"
        for t in tasks
    )
    lab_rows = "".join(
        f"<tr><td>{_esc(l['sample_date'])}</td><td>{_esc(test_name(l, lang))}</td>"
        f"<td>{_esc(l.get('value') if l.get('value') is not None else l.get('value_text', '—'))} {_esc(l.get('unit') or '')}</td>"
        f"<td>{_esc(flag_label(l.get('flag'), lang))}</td></tr>"
        for l in labs[:20]
    )
    brief_items = "".join(
        f"<li>{_esc(i['text_ru'] if lang == 'ru' else i.get('text_en') or i['text_ru'])}</li>"
        for i in brief.get("items", [])
    )
    questions = [L["q1"], L["q2"], L["q3"], L["q4"], L["q5"]]
    q_html = "".join(f"<li>{_esc(q)}</li>" for q in questions)
    headline = brief.get("headline_ru") if lang == "ru" else brief.get("headline_en") or brief.get("headline_ru")

    allergy_rows = "".join(
        f"<tr><td>{_esc(a.get('allergen'))}</td><td>{_esc(a.get('reaction') or '—')}</td>"
        f"<td>{_esc(a.get('severity') or '—')}</td></tr>"
        for a in (user_profile.get("allergies") or []) if a.get("allergen")
    )
    immun_lines = "".join(
        f"<li>{_esc(i.get('name'))}{(' — ' + _esc(i.get('date'))) if i.get('date') else ''}</li>"
        for i in (user_profile.get("immunizations") or []) if i.get("name")
    )
    proc_lines = "".join(
        f"<li>{_esc(p.get('name'))}{(' — ' + _esc(p.get('date'))) if p.get('date') else ''}"
        f"{(': ' + _esc(p.get('notes'))) if p.get('notes') else ''}</li>"
        for p in (user_profile.get("procedures") or []) if p.get("name")
    )
    family_lines = "".join(
        f"<li>{_esc(f.get('relation'))}: {_esc(f.get('condition'))}</li>"
        for f in (user_profile.get("family_history") or []) if f.get("condition")
    )

    brief_items_html = brief_items or f"<li>{L['no_urgent']}</li>"
    # Section id -> HTML block. Assembled in the user-picked order.
    blocks = {
        "diagnoses": f"<h2>{L['diagnoses']}</h2><ul>{diag_lines or '<li>—</li>'}</ul>",
        "week": f"<h2>{L['this_week']}</h2><p>{_esc(headline)}</p><ul>{brief_items_html}</ul>",
        "allergies": (
            f"<h2>{_sec_label('allergies')}</h2><table><thead><tr><th>{_sec_label('allergies')}</th>"
            f"<th>{'Реакция' if lang=='ru' else 'Reaction'}</th><th>{'Тяжесть' if lang=='ru' else 'Severity'}</th></tr></thead>"
            f"<tbody>{allergy_rows or '<tr><td colspan=3>—</td></tr>'}</tbody></table>"
        ),
        "meds": (
            f"<h2>{L['meds']}</h2><table><thead><tr><th>{L['med_name']}</th><th>{L['dose']}</th><th>{L['purpose']}</th></tr></thead>"
            f"<tbody>{med_rows or '<tr><td colspan=3>—</td></tr>'}</tbody></table>"
        ),
        "labs": (
            f"<h2>{L['labs']}</h2><table><thead><tr><th>{L['date']}</th><th>{L['test']}</th><th>{L['value']}</th><th>{L['flag']}</th></tr></thead>"
            f"<tbody>{lab_rows or '<tr><td colspan=4>—</td></tr>'}</tbody></table>"
        ),
        "immunizations": f"<h2>{_sec_label('immunizations')}</h2><ul>{immun_lines or '<li>—</li>'}</ul>",
        "procedures": f"<h2>{_sec_label('procedures')}</h2><ul>{proc_lines or '<li>—</li>'}</ul>",
        "family_history": f"<h2>{_sec_label('family_history')}</h2><ul>{family_lines or '<li>—</li>'}</ul>",
        "tasks": (
            f"<h2>{L['tasks']}</h2><table><thead><tr><th>{L['task']}</th><th>{L['priority']}</th><th>{L['category']}</th></tr></thead>"
            f"<tbody>{task_rows or '<tr><td colspan=3>—</td></tr>'}</tbody></table>"
        ),
        "questions": f"<h2>{L['questions']}</h2><ul>{q_html}</ul>",
    }
    body_sections = "\n  ".join(blocks[s] for s in picked if s in blocks)

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8" />
  <title>{L['title']} — {_esc(profile.get('display_name'))}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; color: #111; line-height: 1.45; }}
    h1 {{ font-size: 1.35rem; margin-bottom: 0.25rem; }}
    h2 {{ font-size: 1rem; margin: 1.5rem 0 0.5rem; border-bottom: 1px solid #ccc; padding-bottom: 0.25rem; }}
    .meta {{ color: #555; font-size: 0.875rem; margin-bottom: 1.5rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.8125rem; margin-top: 0.5rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.5rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    ul {{ margin: 0.35rem 0 0 1.1rem; font-size: 0.875rem; }}
    @media print {{ body {{ margin: 1cm; }} .noprint {{ display: none; }} }}
  </style>
</head>
<body>
  <p class="noprint">{L['print_hint']}</p>
  <h1>{_esc(profile.get('display_name'))} — {L['visit']}</h1>
  <p class="meta">{L['generated']}: {generated} · {L['local_data']}</p>

  {body_sections}

  <p class="meta" style="margin-top:2rem">{L['disclaimer']}</p>
</body>
</html>"""


def export_visit_pack(profile_id: str | None = None, lang: str = "ru",
                      sections: list[str] | None = None) -> Path:
    root = ensure_health_folders(profile_id)
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    lang = normalize_lang(lang)
    html = build_visit_pack_html(profile_id, lang, sections)
    suffix = "" if lang == "ru" else f"_{lang}"
    out = reports / f"visit_pack_{datetime.now().strftime('%Y-%m-%d')}{suffix}.html"
    out.write_text(html, encoding="utf-8")
    latest = reports / f"visit_pack_latest{suffix}.html"
    latest.write_text(html, encoding="utf-8")
    return out
