"""Build dashboard.html with embedded JSON (works with file:// in Safari)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from backend.health_db import dashboard_snapshot, export_dashboard_json
from backend.paths import REPO_ROOT, ensure_health_folders

DASHBOARD_SRC = REPO_ROOT / "dashboard" / "index.html"
DATA_PLACEHOLDER = "<!-- ZAMIRA_DASHBOARD_DATA -->"


def export_dashboard_html(profile_id: str | None = None) -> Path:
    export_dashboard_json(profile_id)
    root = ensure_health_folders(profile_id)
    snapshot = dashboard_snapshot(profile_id)
    snapshot["generated_at"] = datetime.now().isoformat(timespec="seconds")

    if not DASHBOARD_SRC.exists():
        raise FileNotFoundError(DASHBOARD_SRC)

    html = DASHBOARD_SRC.read_text(encoding="utf-8")
    payload = json.dumps(snapshot, ensure_ascii=False)
    # Prevent </script> in embedded JSON from breaking HTML
    payload = payload.replace("<", "\\u003c")
    block = f'<script id="dashboard-data" type="application/json">{payload}</script>'

    if DATA_PLACEHOLDER in html:
        html = html.replace(DATA_PLACEHOLDER, block)
    else:
        html = html.replace("</head>", f"  {block}\n</head>")

    out = root / "dashboard.html"
    out.write_text(html, encoding="utf-8")

    import shutil

    for src, dest in (
        (REPO_ROOT / "dashboard" / "vendor", root / "vendor"),
        (REPO_ROOT / "dashboard" / "icons", root / "icons"),
    ):
        if not src.exists():
            continue
        try:
            shutil.copytree(src, dest, dirs_exist_ok=True)
        except OSError:
            pass

    try:
        from backend.visit_pack import export_visit_pack
        export_visit_pack(profile_id)
    except Exception:
        pass
    try:
        from backend.consilium import export_consilium
        export_consilium(profile_id)
    except Exception:
        pass

    return out
