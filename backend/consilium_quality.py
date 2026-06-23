"""Validate Claude consilium quality — reject shallow template output."""

from __future__ import annotations

import re
from typing import Any

FORBIDDEN_SOLE = re.compile(
    r"^(обсудите|проконсультируйтесь|сходите|идите)\s+.*врач",
    re.I,
)


def _word_count(text: str) -> int:
    return len(text.split())


def validate_specialist(sp: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    sid = sp.get("id") or "?"
    op = sp.get("opinion") or {}
    see = " ".join(op.get("see") or [])
    recs = op.get("recommendations") or []
    evidence = op.get("evidence") or []

    if _word_count(see) < 25:
        issues.append(f"{sid}: «Что вижу» слишком коротко ({_word_count(see)} слов) — нужен связный текст с цифрами")

    if len(recs) < 2:
        issues.append(f"{sid}: нужно минимум 2 конкретные рекомендации")

    actionable = 0
    for r in recs:
        rs = str(r).strip()
        if not rs:
            continue
        if FORBIDDEN_SOLE.match(rs) and _word_count(rs) < 8:
            issues.append(f"{sid}: рекомендация слишком общая: «{rs[:50]}…»")
        else:
            actionable += 1
    if actionable < 2:
        issues.append(f"{sid}: рекомендации должны быть конкретными (доза/срок/действие)")

    if len(evidence) < 2:
        issues.append(f"{sid}: нужно минимум 2 пункта evidence (lab/guideline/imaging)")

    return issues


def validate_consilium(specialists: list[dict]) -> dict[str, Any]:
    all_issues: list[str] = []
    for sp in specialists:
        all_issues.extend(validate_specialist(sp))
    return {
        "ok": len(all_issues) == 0,
        "issues": all_issues,
        "message_ru": (
            "Качество достаточное для дашборда."
            if not all_issues
            else "Консилиум слишком поверхностный — Claude должен переписать глубже: " + "; ".join(all_issues[:5])
        ),
    }
