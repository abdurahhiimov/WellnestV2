"""Resolve active profile and filesystem paths."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"


def active_profile_id() -> str:
    return os.environ.get("ACTIVE_PROFILE", "user")


def profile_dir(profile_id: str | None = None) -> Path:
    pid = profile_id or active_profile_id()
    return PROFILES_DIR / pid


def _read_legacy_context(profile_id: str | None = None) -> dict | None:
    """Raw read of a shipped profiles/<id>/profile_context.json, or None.

    Used by health_root WITHOUT touching profile_store, to avoid recursion
    (profile_store.load_profile -> health_root -> here).
    """
    path = profile_dir(profile_id) / "profile_context.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _context_from_profile_store(profile_id: str | None = None) -> dict | None:
    """Build a legacy-shaped context from the new profile.json, or None."""
    from backend.profile_store import load_profile  # lazy: avoids import cycle

    prof = load_profile(profile_id)
    if not prof.get("display_name") and not prof.get("conditions"):
        return None  # truly empty / not onboarded
    return {
        "profile_id": prof.get("profile_id", "me"),
        "display_name": prof.get("display_name", ""),
        "birth_year": prof.get("birth_year") or 1970,
        "sex": prof.get("sex", ""),
        "language_primary": prof.get("language_primary", "en"),
        "diagnoses": [
            {"code": c.get("code", ""), "label_ru": c.get("label", ""), "status": c.get("status", "active")}
            for c in (prof.get("conditions") or [])
        ],
        "medications": prof.get("medications", []),
        "nutraceuticals_count": 0,
        "last_labs_note": "",
        "gp_persona": {},
        "location_folder": prof.get("location_folder", "~/Desktop/HEALTH"),
    }


def load_profile_context(profile_id: str | None = None) -> dict:
    legacy = _read_legacy_context(profile_id)
    if legacy is not None:
        return legacy
    ctx = _context_from_profile_store(profile_id)
    if ctx is not None:
        return ctx
    raise FileNotFoundError(f"Profile not found for: {profile_id or active_profile_id()}")


def health_root(profile_id: str | None = None) -> Path:
    if override := (os.environ.get("WELLNEST_HEALTH_ROOT") or os.environ.get("ZAMIRA_HEALTH_ROOT")):
        return Path(override).expanduser()

    # Prefer the legacy shipped profile's folder if present (keeps existing
    # installs pointing at their HEALTH dir); otherwise default. Reads the legacy
    # file directly — never via profile_store — to avoid an import cycle.
    legacy = _read_legacy_context(profile_id)
    folder = (legacy or {}).get("location_folder", "~/Desktop/Wellnest")
    return Path(folder).expanduser()


def db_path(profile_id: str | None = None) -> Path:
    return health_root(profile_id) / "data" / "health.db"


def ensure_health_folders(profile_id: str | None = None) -> Path:
    root = health_root(profile_id)
    for sub in ("data", "new_labs", "reports", "imports", "inbox", "uploads", "health_auto_export", "wearables"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
