"""Shared consilium presentation: emojis, evidence blocks, HTML helpers."""

from __future__ import annotations

import re
from html import escape
from typing import Any

SPECIALIST_EMOJI: dict[str, str] = {
    "endo": "🔬",
    "gyn": "🌸",
    "neuro": "🧠",
    "nutri": "🥗",
    "ortho": "🦴",
    "gp": "🩺",
}

SECTION_UI = {
    "see": {"icon": "🔍", "label_ru": "Что вижу", "label_en": "What I see"},
    "concerns": {"icon": "⚠️", "label_ru": "Что настораживает", "label_en": "Concerns"},
    "recommendations": {"icon": "✅", "label_ru": "Рекомендации", "label_en": "Recommendations"},
    "reasoning": {"icon": "📎", "label_ru": "На основе чего", "label_en": "Evidence"},
}

EVIDENCE_KIND_LABEL: dict[str, str] = {
    "lab": "Анализ",
    "task": "Задача",
    "checkin": "Check-in",
    "guideline": "Гайдлайн",
    "study": "Исследование",
    "profile": "Профиль",
    "imaging": "Снимок",
    "medication": "Препарат",
}


def _esc(s: Any) -> str:
    return escape(str(s or ""))


def sanitize_clinical_text(text: str) -> str:
    """Strip runaway template tokens some free models emit (e.g. {{{{}{}…)."""
    if not text:
        return ""
    t = str(text).strip()
    # Cut at the first run of broken braces / empty template pairs.
    m = re.search(r"\{{2,}|\}{2,}|(?:\{\}){4,}", t)
    if m:
        t = t[: m.start()].rstrip(" ,.;:—–-(")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _as_lines(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        t = sanitize_clinical_text(val)
        return [t] if t else []
    if isinstance(val, list):
        out = []
        for x in val:
            t = sanitize_clinical_text(str(x))
            if t:
                out.append(t)
        return out
    t = sanitize_clinical_text(str(val))
    return [t] if t else []


def normalize_evidence(raw: list | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            t = item.strip()
            if t:
                out.append({"claim_ru": t, "kind": "profile", "source_label": t})
            continue
        if not isinstance(item, dict):
            continue
        claim = (item.get("claim_ru") or item.get("text") or item.get("claim") or "").strip()
        if not claim:
            continue
        out.append(
            {
                "claim_ru": claim,
                "kind": item.get("kind") or item.get("type") or "profile",
                "ref": item.get("ref") or item.get("test_code"),
                "date": item.get("date") or item.get("sample_date"),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "source_label": item.get("source_label") or item.get("source") or "",
                "source_url": item.get("source_url") or item.get("url"),
                "study_title": item.get("study_title") or item.get("title"),
                "study_url": item.get("study_url") or item.get("study_link"),
            }
        )
    return out


def normalize_opinion(raw: dict | None) -> dict[str, Any]:
    """Normalize opinion dict; preserves evidence array."""
    keys = ("see", "concerns", "recommendations", "reasoning")
    out: dict[str, Any] = {k: [] for k in keys}
    if not raw:
        out["evidence"] = []
        return out
    for key in keys:
        out[key] = _as_lines(raw.get(key))
    out["evidence"] = normalize_evidence(raw.get("evidence"))
    return out


def evidence_from_reasoning_lines(reasoning: list[str]) -> list[dict[str, Any]]:
    return [{"claim_ru": line, "kind": "profile", "source_label": line} for line in reasoning if line]


def merge_evidence(opinion: dict[str, Any]) -> list[dict[str, Any]]:
    ev = list(opinion.get("evidence") or [])
    if not ev and opinion.get("reasoning"):
        ev = evidence_from_reasoning_lines(opinion["reasoning"])
    return ev


def render_evidence_html(evidence: list[dict], lang: str = "ru") -> str:
    if not evidence:
        return ""
    items = []
    for ev in evidence:
        kind = EVIDENCE_KIND_LABEL.get(ev.get("kind", ""), ev.get("kind", "источник"))
        claim = _esc(ev.get("claim_ru", ""))
        meta_parts = []
        if ev.get("date"):
            meta_parts.append(_esc(ev["date"]))
        if ev.get("value") is not None:
            meta_parts.append(f"{_esc(ev['value'])} {_esc(ev.get('unit') or '')}".strip())
        if ev.get("source_label"):
            meta_parts.append(_esc(ev["source_label"]))
        meta = " · ".join(meta_parts)
        link = ev.get("study_url") or ev.get("source_url")
        link_html = ""
        if link:
            title = ev.get("study_title") or link
            link_html = f' <a href="{_esc(link)}" target="_blank" rel="noopener">{_esc(title)}</a>'
        meta_html = f'<span class="ev-meta">{meta}</span>' if meta else ""
        items.append(
            f'<li class="ev-item"><span class="ev-kind">{_esc(kind)}</span> '
            f'<span class="ev-claim">{claim}</span>'
            f"{meta_html}"
            f"{link_html}</li>"
        )
    return f'<ul class="ev-list">{"".join(items)}</ul>'


def render_specialist_card_html(
    sp: dict[str, Any],
    *,
    lang: str = "ru",
    compact: bool = False,
) -> str:
    sid = sp.get("id") or ""
    emoji = SPECIALIST_EMOJI.get(sid, "👤")
    title = sp.get("title_ru" if lang == "ru" else "title_en") or sp.get("title_ru") or sid
    focus = sp.get("focus_ru") if lang == "ru" else sp.get("focus_en", sp.get("focus_ru"))
    opinion = sp.get("opinion") or {}
    if isinstance(opinion, dict) and "see" not in opinion:
        opinion = normalize_opinion(opinion)
    else:
        opinion = normalize_opinion(opinion)

    gp_cls = " spec-gp" if sid == "gp" else ""
    sections = []

    for key in ("see", "concerns", "recommendations"):
        ui = SECTION_UI[key]
        label = ui["label_ru"] if lang == "ru" else ui["label_en"]
        lines = opinion.get(key) or []
        if not lines:
            continue
        if key == "recommendations":
            body = "<ul>" + "".join(f"<li>{_esc(x)}</li>" for x in lines) + "</ul>"
        else:
            body = "".join(f'<p class="spec-p">{_esc(x)}</p>' for x in lines)
        sections.append(
            f'<div class="spec-sec spec-sec-{key}">'
            f'<h5>{ui["icon"]} {_esc(label)}</h5>{body}</div>'
        )

    evidence = merge_evidence(opinion)
    if evidence:
        ui = SECTION_UI["reasoning"]
        label = ui["label_ru"] if lang == "ru" else ui["label_en"]
        sections.append(
            f'<div class="spec-sec spec-sec-evidence">'
            f'<h5>{ui["icon"]} {_esc(label)}</h5>{render_evidence_html(evidence, lang)}</div>'
        )
    elif opinion.get("reasoning"):
        ui = SECTION_UI["reasoning"]
        label = ui["label_ru"] if lang == "ru" else ui["label_en"]
        body = "".join(f'<p class="spec-p">{_esc(x)}</p>' for x in opinion["reasoning"])
        sections.append(f'<div class="spec-sec spec-sec-evidence"><h5>{ui["icon"]} {_esc(label)}</h5>{body}</div>')

    focus_html = f'<p class="spec-focus">{_esc(focus)}</p>' if focus and not compact else ""
    inner = "".join(sections) or f'<p class="spec-p muted">{_esc("Нет данных")}</p>'

    return (
        f'<article class="spec-card{gp_cls}" data-spec="{_esc(sid)}">'
        f'<header class="spec-head"><span class="spec-emoji">{emoji}</span>'
        f'<h4 class="spec-title">{_esc(title)}</h4></header>'
        f"{focus_html}{inner}</article>"
    )


def render_consilium_body_html(specialists: list[dict], lang: str = "ru") -> str:
    return "".join(render_specialist_card_html(sp, lang=lang) for sp in specialists)


def render_symptom_answer_html(answer: dict[str, Any], lang: str = "ru") -> str:
    if not answer:
        return ""
    summary_parts = [p.strip() for p in (answer.get("summary_ru") or "").split("\n\n") if p.strip()]
    summary_html = "".join(f'<p class="spec-p">{_esc(p)}</p>' for p in summary_parts)
    links = answer.get("possible_links_ru") or []
    discuss = _esc(answer.get("discuss_with_doctor_ru", ""))
    q = _esc(answer.get("question", ""))
    links_html = ""
    if links:
        links_html = "<ul>" + "".join(f"<li>{_esc(x)}</li>" for x in links) + "</ul>"
    ev_html = render_evidence_html(answer.get("evidence") or [], lang)
    return f"""
    <div class="sym-answer">
      <p class="sym-q"><strong>Вопрос:</strong> {q}</p>
      <div class="sym-summary">{summary_html}</div>
      {f'<div class="spec-sec"><h5>🔗 Возможные связи</h5>{links_html}</div>' if links_html else ''}
      {f'<div class="spec-sec spec-sec-evidence"><h5>📎 На основе чего</h5>{ev_html}</div>' if ev_html else ''}
      {f'<p class="sym-doctor"><strong>Обсудите с врачом:</strong> {discuss}</p>' if discuss else ''}
    </div>"""
