"""HTML reports for symptom sessions (print to PDF from browser)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from backend.paths import ensure_health_folders
from backend.report_locale import SYMPTOM_REPORT, normalize_lang


def export_symptom_report(
    question: str,
    answer: dict[str, Any],
    attachments: list[str] | None = None,
    profile_id: str | None = None,
    lang: str = "ru",
) -> dict[str, Any]:
    lang = normalize_lang(lang)
    L = SYMPTOM_REPORT[lang]
    root = ensure_health_folders(profile_id)
    path = root / "reports" / f"symptom_session{'' if lang == 'ru' else f'_{lang}'}.html"
    q = escape(question)
    summary = escape(answer.get("summary_ru") or "")
    discuss = escape(answer.get("discuss_with_doctor_ru") or "")
    links = answer.get("possible_links_ru") or []
    links_html = "".join(f"<li>{escape(x)}</li>" for x in links)
    att_html = ""
    if attachments:
        att_html = "<ul>" + "".join(f"<li>{escape(a)}</li>" for a in attachments) + "</ul>"
    html = f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"/>
<title>{L['title']}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; line-height: 1.55; color: #111; }}
h1 {{ font-size: 1.25rem; }} .muted {{ color: #666; font-size: 0.9rem; }}
section {{ margin: 1.25rem 0; }} ul {{ padding-left: 1.2rem; }}
@media print {{ body {{ margin: 1cm; }} }}
</style></head><body>
<h1>{L['title']}</h1>
<p class="muted">{L['generated']} {escape(datetime.now().strftime("%Y-%m-%d %H:%M"))} · Wellnest</p>
<section><strong>{L['question']}:</strong><p>{q}</p></section>
<section><strong>{L['analysis']}:</strong><p>{summary.replace(chr(10), '</p><p>')}</p></section>
{f'<section><strong>{L["links"]}:</strong><ul>{links_html}</ul></section>' if links_html else ''}
{f'<section><strong>{L["discuss"]}:</strong><p>{discuss}</p></section>' if discuss else ''}
{f'<section><strong>{L["attachments"]}:</strong>{att_html}</section>' if att_html else ''}
<p class="muted">{L['disclaimer']}</p>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    url = "/reports/symptom_session.html" if lang == "ru" else f"/reports/symptom_session_{lang}.html"
    return {"ok": True, "path": str(path), "url": url, "filename": path.name}
