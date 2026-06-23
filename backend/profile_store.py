"""User profile: the single source of truth for personalization.

A profile lives at HEALTH/data/profile.json (user-owned, per install). It drives
demographics in prompts, clinical reference ranges, and the specialist panel.

Backwards compatibility: if no profile.json exists yet but a legacy shipped
profile (profiles/<id>/profile_context.json, e.g. zamira) is present, it is
migrated in on first read and marked onboarding_complete=True so existing users
never see the onboarding wizard.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.paths import active_profile_id, health_root, profile_dir

SCHEMA_VERSION = 2

# Canonical empty profile. `profiles` is a forward-looking single-element list so
# multi-profile can be added later without a schema break; today we use [0].
DEFAULTS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "onboarding_complete": False,
    "profile_id": "me",
    "display_name": "",
    "sex": "",                 # "female" | "male" (biological — drives ranges/specialists)
    "gender_identity": "",     # optional, free text
    "birth_year": None,
    "language_primary": "en",  # "en" | "ru"
    "conditions": [],          # [{ "code", "label", "status", "related_labs": [test_code] }]
    "medications": [],         # [{ "name", "dose", "purpose", "treats": [condition_code] }]
    "allergies": [],           # [{ "allergen", "reaction", "severity": mild|moderate|severe }]
    "immunizations": [],       # [{ "name", "date" }]
    "procedures": [],          # [{ "name", "date", "notes" }]
    "family_history": [],      # [{ "relation", "condition" }]
    "emergency_contacts": [],  # [{ "name", "relation", "phone" }]
    "providers": [],           # [{ "name", "specialty", "phone", "kind": doctor|pharmacy }]
    "concerns": [],            # free-text concern strings from intake
    "concern_tags": [],        # normalized tags (e.g. "sleep", "fatigue")
    "specialist_panel": [],    # list of specialist ids (from specialist_catalog.json)
    "location_folder": "~/Desktop/Wellnest",
    "created_at": None,
    "updated_at": None,
}


def profile_path(profile_id: str | None = None) -> Path:
    return health_root(profile_id) / "data" / "profile.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrate_from_legacy(profile_id: str | None = None) -> dict[str, Any] | None:
    """Build a profile dict from a shipped profiles/<id>/profile_context.json."""
    legacy = profile_dir(profile_id) / "profile_context.json"
    if not legacy.exists():
        return None
    try:
        ctx = json.loads(legacy.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    prof = dict(DEFAULTS)
    prof.update(
        {
            "onboarding_complete": True,  # existing user: never show the wizard
            "profile_id": ctx.get("profile_id") or profile_id or "me",
            "display_name": ctx.get("display_name", ""),
            "sex": ctx.get("sex", ""),
            "birth_year": ctx.get("birth_year"),
            "language_primary": ctx.get("language_primary", "ru"),
            "conditions": [
                {
                    "code": d.get("code", ""),
                    "label": d.get("label_ru") or d.get("label") or d.get("code", ""),
                    "status": d.get("status", "active"),
                }
                for d in (ctx.get("diagnoses") or [])
            ],
            "medications": [
                {
                    "name": m.get("name", ""),
                    "dose": m.get("dose", ""),
                    "purpose": m.get("purpose", ""),
                }
                for m in (ctx.get("medications") or [])
                if m.get("status") != "stopped"
            ],
            "location_folder": ctx.get("location_folder", "~/Desktop/HEALTH"),
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    return prof


def load_profile(profile_id: str | None = None) -> dict[str, Any]:
    """Load the live profile. Migrates a legacy profile on first read.

    Returns DEFAULTS (onboarding_complete=False) for a brand-new install with no
    profile.json and no shipped legacy profile — that triggers the onboarding wizard.
    """
    path = profile_path(profile_id)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            pass

    migrated = _migrate_from_legacy(profile_id)
    if migrated is not None:
        save_profile(migrated, profile_id)
        return migrated

    base = dict(DEFAULTS)
    base["profile_id"] = profile_id or active_profile_id()
    return base


def save_profile(profile: dict[str, Any], profile_id: str | None = None) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(profile)
    merged["schema_version"] = SCHEMA_VERSION
    if not merged.get("created_at"):
        merged["created_at"] = _now()
    merged["updated_at"] = _now()

    path = profile_path(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def update_profile(patch: dict[str, Any], profile_id: str | None = None) -> dict[str, Any]:
    current = load_profile(profile_id)
    current.update(patch)
    return save_profile(current, profile_id)


def is_onboarded(profile_id: str | None = None) -> bool:
    return bool(load_profile(profile_id).get("onboarding_complete"))


def age_from_profile(profile: dict[str, Any]) -> int | None:
    by = profile.get("birth_year")
    if not by:
        return None
    try:
        return datetime.now().year - int(by)
    except (TypeError, ValueError):
        return None
