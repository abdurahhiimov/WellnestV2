#!/usr/bin/env python3
"""Regenerate dashboard.html with latest data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.dashboard_export import export_dashboard_html  # noqa: E402
from backend.paths import active_profile_id  # noqa: E402


def main() -> None:
    profile = active_profile_id()
    path = export_dashboard_html(profile)
    print(f"Dashboard updated: {path}")
    print("Open: bash scripts/start.command  →  http://127.0.0.1:8787/app/")


if __name__ == "__main__":
    main()
