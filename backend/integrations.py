"""Load integration config and paths."""

from __future__ import annotations

import json
from pathlib import Path

from backend.paths import health_root


def integrations_path() -> Path:
    return health_root() / "data" / "integrations.json"


def load_integrations() -> dict:
    path = integrations_path()
    example = Path(__file__).resolve().parent.parent / "profiles/default/integrations.example.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if example.exists():
        return json.loads(example.read_text(encoding="utf-8"))
    return {}


def oura_configured() -> bool:
    cfg = load_integrations().get("oura", {})
    cid = cfg.get("client_id", "")
    return bool(cid and cid != "YOUR_OURA_CLIENT_ID" and cfg.get("client_secret"))
