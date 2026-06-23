"""Determine the specialist panel for a profile.

Hybrid approach:
  1. Rule engine (deterministic, offline-safe) picks a core panel from the
     catalog based on sex / age / condition codes / concern tags. 'gp' always in.
  2. Optional LLM refinement suggests extra specialists from free-text concerns
     (skipped gracefully when no API key is configured).
The user confirms/edits the final panel in onboarding.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "specialist_catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_specialists() -> list[dict[str, Any]]:
    return load_catalog().get("specialists", [])


def specialist_by_id(spec_id: str) -> dict[str, Any] | None:
    for s in catalog_specialists():
        if s.get("id") == spec_id:
            return s
    return None


def localized_specialists(language: str = "en") -> list[dict[str, Any]]:
    """Catalog flattened for the UI in one language."""
    lang = "ru" if language == "ru" else "en"
    out = []
    for s in catalog_specialists():
        out.append(
            {
                "id": s["id"],
                "name": (s.get("name") or {}).get(lang) or (s.get("name") or {}).get("en", s["id"]),
                "focus": (s.get("focus") or {}).get(lang) or (s.get("focus") or {}).get("en", ""),
                "always": bool(s.get("always")),
            }
        )
    return out


def _matches(spec: dict[str, Any], *, sex: str, age: int | None,
             condition_codes: set[str], concern_tags: set[str],
             has_supplements: bool) -> bool:
    rules = spec.get("rules") or {}

    # Sex gate: if a specialist is sex-restricted, the profile sex must match.
    allowed_sex = rules.get("sex")
    if allowed_sex and sex and sex not in allowed_sex:
        return False

    if rules.get("always_if_supplements") and has_supplements:
        return True

    if condition_codes & set(rules.get("condition_codes") or []):
        return True
    if concern_tags & set(rules.get("concern_tags") or []):
        return True

    age_min = rules.get("age_min")
    # age_min alone is a soft signal: only include on age if there is also any
    # condition/concern overlap handled above; bare age does not add a specialist.
    return False


def select_panel(profile: dict[str, Any]) -> list[str]:
    """Rule-based core panel. Returns ordered list of specialist ids."""
    from backend.profile_store import age_from_profile

    sex = (profile.get("sex") or "").lower()
    age = age_from_profile(profile)
    condition_codes = {
        str(c.get("code", "")).lower()
        for c in (profile.get("conditions") or [])
        if c.get("code")
    }
    concern_tags = {str(t).lower() for t in (profile.get("concern_tags") or [])}
    has_supplements = bool(profile.get("medications"))

    panel: list[str] = []
    for spec in catalog_specialists():
        sid = spec["id"]
        if spec.get("always"):
            panel.append(sid)
            continue
        if _matches(
            spec,
            sex=sex,
            age=age,
            condition_codes=condition_codes,
            concern_tags=concern_tags,
            has_supplements=has_supplements,
        ):
            panel.append(sid)

    # Keep panel to a sensible size; gp always first.
    if "gp" in panel:
        panel = ["gp"] + [s for s in panel if s != "gp"]
    return panel


def suggest_panel_llm(profile: dict[str, Any], base_panel: list[str]) -> list[str]:
    """Ask the LLM to add specialists justified by free-text concerns.

    Returns extra specialist ids (subset of the catalog, excluding base_panel).
    Returns [] if the engine is disabled or anything goes wrong — never raises.
    """
    try:
        from backend.llm_engine import _chat, engine_config

        if not engine_config().get("enabled"):
            return []

        concerns = profile.get("concerns") or []
        if not concerns:
            return []

        catalog = [
            {"id": s["id"], "focus": (s.get("focus") or {}).get("en", "")}
            for s in catalog_specialists()
        ]
        system = (
            "You map a patient's free-text health concerns to relevant medical "
            "specialists from a fixed catalog. Be conservative. Return only "
            "specialists clearly justified by the concerns."
        )
        user = (
            "CATALOG (id: focus):\n" + json.dumps(catalog, ensure_ascii=False, indent=2)
            + "\n\nALREADY SELECTED: " + json.dumps(base_panel)
            + "\n\nPATIENT CONCERNS: " + json.dumps(concerns, ensure_ascii=False)
            + "\n\nReturn STRICT JSON: {\"add\": [\"id\", ...]} — only ids from the "
            "catalog that are NOT already selected and are justified. Empty list if none."
        )
        raw = _chat(system, user, want_json=True, max_tokens=400)
        data = json.loads(_first_json(raw))
        valid = {s["id"] for s in catalog_specialists()}
        return [i for i in (data.get("add") or []) if i in valid and i not in base_panel]
    except Exception:
        return []


def _first_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else "{}"


def recommend_panel(profile: dict[str, Any], use_llm: bool = True) -> dict[str, Any]:
    """Full hybrid recommendation. Returns {panel, rule_based, llm_added}."""
    base = select_panel(profile)
    llm_added: list[str] = []
    if use_llm:
        llm_added = suggest_panel_llm(profile, base)
    panel = base + [s for s in llm_added if s not in base]
    return {"panel": panel, "rule_based": base, "llm_added": llm_added}
