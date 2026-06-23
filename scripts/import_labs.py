#!/usr/bin/env python3
"""Import lab results from JSON (manual entry from photos or OCR)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import health_db  # noqa: E402
from backend.dashboard_export import export_dashboard_html  # noqa: E402
from backend.paths import active_profile_id, health_root  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import labs from JSON file")
    parser.add_argument(
        "json_file",
        nargs="?",
        default=str(ROOT / "data/imports/labs_may_2026.json"),
        help="Path to JSON with results array",
    )
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    profile = args.profile or active_profile_id()
    src = Path(args.json_file).expanduser().resolve()
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    root = health_root(profile)
    dest = root / "imports" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    count = health_db.import_lab_results_from_json(dest, profile)
    dashboard = export_dashboard_html(profile)

    print(f"Imported {count} lab result(s) from {src.name}")
    print(f"Dashboard: {dashboard}")
    print("Refresh Safari: Cmd+R on ~/Desktop/HEALTH/dashboard.html")


if __name__ == "__main__":
    main()
