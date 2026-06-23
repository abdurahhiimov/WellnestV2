"""Oura Ring API v2 — OAuth + sync (free personal API)."""

from __future__ import annotations

import json
import secrets
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from backend import health_db
from backend.integrations import load_integrations
from backend.wearables import _log_sync, ensure_wearables_tables, upsert_daily_metric

OURA_AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"
OURA_API = "https://api.ouraring.com/v2/usercollection"
SCOPES = "email personal daily heartrate tag workout session"


def _oura_cfg() -> dict:
    return load_integrations().get("oura", {})


def get_oauth_url(state: str) -> str:
    cfg = _oura_cfg()
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg.get("redirect_uri", "http://127.0.0.1:8787/oura/callback"),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    }
    return f"{OURA_AUTH_URL}?{urllib.parse.urlencode(params)}"


def save_tokens(token_payload: dict, profile_id: str | None = None) -> None:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    expires_in = token_payload.get("expires_in", 86400)
    expires_at = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat()
    conn.execute(
        """
        INSERT INTO integration_tokens(provider, access_token, refresh_token, expires_at, scope, metadata_json, updated_at)
        VALUES ('oura', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            expires_at=excluded.expires_at,
            scope=excluded.scope,
            metadata_json=excluded.metadata_json,
            updated_at=excluded.updated_at
        """,
        (
            token_payload["access_token"],
            token_payload.get("refresh_token"),
            expires_at,
            token_payload.get("scope"),
            json.dumps({"token_type": token_payload.get("token_type")}),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_access_token(profile_id: str | None = None) -> str | None:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    row = conn.execute("SELECT * FROM integration_tokens WHERE provider = 'oura'").fetchone()
    conn.close()
    if not row:
        return None
    if row["expires_at"]:
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp < datetime.utcnow() and row["refresh_token"]:
                return refresh_access_token(row["refresh_token"], profile_id)
        except ValueError:
            pass
    return row["access_token"]


def exchange_code(code: str, profile_id: str | None = None) -> dict:
    cfg = _oura_cfg()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg.get("redirect_uri", "http://127.0.0.1:8787/oura/callback"),
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    resp = httpx.post(OURA_TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    save_tokens(payload, profile_id)
    return payload


def refresh_access_token(refresh_token: str, profile_id: str | None = None) -> str | None:
    cfg = _oura_cfg()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    resp = httpx.post(OURA_TOKEN_URL, data=data, timeout=30)
    if resp.status_code != 200:
        return None
    payload = resp.json()
    save_tokens(payload, profile_id)
    return payload.get("access_token")


def is_connected(profile_id: str | None = None) -> bool:
    return get_access_token(profile_id) is not None


def sync_oura(days: int = 30, profile_id: str | None = None) -> dict[str, Any]:
    token = get_access_token(profile_id)
    if not token:
        return {"ok": False, "error": "Oura not connected"}

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    headers = {"Authorization": f"Bearer {token}"}
    added = 0

    endpoints = [
        ("daily_sleep", _map_sleep),
        ("daily_readiness", _map_readiness),
        ("daily_activity", _map_activity),
    ]

    with httpx.Client(headers=headers, timeout=60) as client:
        for collection, mapper in endpoints:
            url = f"{OURA_API}/{collection}?start_date={start}&end_date={end}"
            try:
                resp = client.get(url)
                resp.raise_for_status()
                items = resp.json().get("data") or []
                for item in items:
                    day = item.get("day") or item.get("timestamp", "")[:10]
                    for metric_type, value, unit in mapper(item):
                        if upsert_daily_metric(day, metric_type, value, unit, "oura", profile_id):
                            added += 1
            except Exception as exc:
                _log_sync("oura", "error", f"{collection}: {exc}", 0, profile_id)

    _log_sync("oura", "ok", f"Synced {days}d", added, profile_id)
    return {"ok": True, "records_upserted": added}


def _map_sleep(item: dict) -> list[tuple[str, float | None, str | None]]:
    out: list[tuple[str, float | None, str | None]] = []
    day = item.get("day", "")
    total = item.get("total_sleep_duration")
    if total is not None:
        out.append(("sleep_hours", total / 3600.0, "hours"))
    score = item.get("score")
    if score is not None:
        out.append(("sleep_score", float(score), "score"))
    contrib = item.get("contributors") or {}
    if contrib.get("deep_sleep") is not None:
        out.append(("deep_sleep_score", float(contrib["deep_sleep"]), "score"))
    return out


def _map_readiness(item: dict) -> list[tuple[str, float | None, str | None]]:
    out: list[tuple[str, float | None, str | None]] = []
    if item.get("score") is not None:
        out.append(("readiness_score", float(item["score"]), "score"))
    contrib = item.get("contributors") or {}
    if contrib.get("resting_heart_rate") is not None:
        out.append(("oura_rhr_contrib", float(contrib["resting_heart_rate"]), "score"))
    if contrib.get("hrv_balance") is not None:
        out.append(("hrv_balance", float(contrib["hrv_balance"]), "score"))
    return out


def _map_activity(item: dict) -> list[tuple[str, float | None, str | None]]:
    out: list[tuple[str, float | None, str | None]] = []
    if item.get("steps") is not None:
        out.append(("steps", float(item["steps"]), "steps"))
    if item.get("active_calories") is not None:
        out.append(("active_calories", float(item["active_calories"]), "kcal"))
    if item.get("score") is not None:
        out.append(("activity_score", float(item["score"]), "score"))
    return out


def new_oauth_state() -> str:
    return secrets.token_urlsafe(16)
