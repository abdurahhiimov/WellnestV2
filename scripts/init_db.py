#!/usr/bin/env python3
"""Initialize SQLite and seed profile data."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import health_db  # noqa: E402
from backend.dashboard_export import export_dashboard_html  # noqa: E402
from backend.paths import active_profile_id, ensure_health_folders  # noqa: E402


def _ensure_reference_db(offline_only: bool = True) -> None:
    from backend import reference_db

    if reference_db.reference_db_exists():
        return
    print("Reference DB missing — building...")
    script = ROOT / "scripts" / "download_reference_db.py"
    args = [sys.executable, str(script)]
    if offline_only:
        args.append("--offline")
    subprocess.run(args, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Init Wellnest database")
    parser.add_argument("--profile", default=None, help="Profile id (default: ACTIVE_PROFILE or 'user')")
    parser.add_argument("--skip-reference", action="store_true", help="Do not build reference.db")
    parser.add_argument(
        "--fetch-rxnorm",
        action="store_true",
        help="Download RxNorm interactions (requires network); default is curated-only offline build",
    )
    args = parser.parse_args()

    if not args.skip_reference:
        if args.fetch_rxnorm:
            script = ROOT / "scripts" / "download_reference_db.py"
            subprocess.run([sys.executable, str(script)], check=False)
        else:
            _ensure_reference_db(offline_only=True)

    profile = args.profile or active_profile_id()
    root = ensure_health_folders(profile)
    db = health_db.init_db(profile)
    health_db.seed_from_profile(profile)
    dashboard_path = export_dashboard_html(profile)

    print(f"Profile: {profile}")
    print(f"Health folder: {root}")
    print(f"Database: {db}")
    print(f"Dashboard: {dashboard_path}")
    print("Done.")


if __name__ == "__main__":
    main()
