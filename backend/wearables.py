"""Wearables: Health Auto Export + daily metrics storage."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import health_db
from backend.paths import health_root
from backend.wearables_schema import WEARABLES_SCHEMA

# Health Auto Export metric name → internal type
HAE_METRIC_MAP = {
    "heart_rate": "resting_hr",
    "resting_heart_rate": "resting_hr",
    "heart_rate_variability_sdnn": "hrv_sdnn",
    "step_count": "steps",
    "apple_exercise_time": "exercise_minutes",
    "active_energy_burned": "active_calories",
    "apple_stand_time": "stand_minutes",
    "oxygen_saturation": "spo2",
    "body_mass": "weight_kg",
    "blood_pressure_systolic": "bp_systolic",
    "blood_pressure_diastolic": "bp_diastolic",
    "sleep_analysis": "sleep_hours",
    "apple_sleeping_wrist_temperature": "wrist_temp",
}


def ensure_wearables_tables(profile_id: str | None = None) -> None:
    conn = health_db.connect(profile_id)
    conn.executescript(WEARABLES_SCHEMA)
    conn.commit()
    conn.close()


def _parse_date(raw: str) -> str:
    """Normalize to YYYY-MM-DD."""
    raw = raw.strip()
    if len(raw) >= 10 and raw[4] == "-":
        return raw[:10]
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return raw[:10] if len(raw) >= 10 else datetime.now().strftime("%Y-%m-%d")


def upsert_daily_metric(
    metric_date: str,
    metric_type: str,
    value: float | None,
    unit: str | None,
    source: str,
    profile_id: str | None = None,
    metadata: dict | None = None,
) -> bool:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            """
            INSERT INTO daily_metrics(metric_date, metric_type, value, unit, source, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_date, metric_type, source) DO UPDATE SET
                value=excluded.value, unit=excluded.unit, metadata_json=excluded.metadata_json, created_at=excluded.created_at
            """,
            (
                metric_date,
                metric_type,
                value,
                unit,
                source,
                json.dumps(metadata) if metadata else None,
                now,
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def _aggregate_by_day(entries: list[dict], agg: str = "avg") -> dict[str, float]:
    """Group qty samples by calendar day."""
    buckets: dict[str, list[float]] = {}
    for item in entries:
        qty = item.get("qty")
        if qty is None:
            continue
        day = _parse_date(str(item.get("date", "")))
        buckets.setdefault(day, []).append(float(qty))

    out: dict[str, float] = {}
    for day, vals in buckets.items():
        if agg == "sum":
            out[day] = sum(vals)
        elif agg == "max":
            out[day] = max(vals)
        elif agg == "min":
            out[day] = min(vals)
        else:
            out[day] = sum(vals) / len(vals)
    return out


def import_health_auto_export_file(path: Path, profile_id: str | None = None) -> int:
    """Parse Health Auto Export JSON into daily_metrics."""
    ensure_wearables_tables(profile_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload.get("data") or payload
    metrics = data.get("metrics") or []
    added = 0

    agg_rules = {
        "step_count": "sum",
        "active_energy_burned": "sum",
        "apple_exercise_time": "sum",
        "apple_stand_time": "sum",
        "sleep_analysis": "sum",
    }

    for metric in metrics:
        name = metric.get("name") or metric.get("type") or ""
        internal = HAE_METRIC_MAP.get(name)
        if not internal:
            continue
        entries = metric.get("data") or []
        if not entries:
            continue
        unit = metric.get("units")
        agg = agg_rules.get(name, "avg")
        by_day = _aggregate_by_day(entries, agg=agg)
        for day, val in by_day.items():
            if internal == "sleep_hours" and unit and "hr" not in str(unit).lower():
                val = val / 3600.0 if val > 24 else val
            if upsert_daily_metric(day, internal, val, unit, "health_auto_export", profile_id):
                added += 1

    _log_sync("health_auto_export", "ok", f"Imported {path.name}", added, profile_id)
    return added


def import_health_auto_export_folder(profile_id: str | None = None) -> dict[str, Any]:
    root = health_root(profile_id)
    folder = root / "health_auto_export"
    folder.mkdir(parents=True, exist_ok=True)

    scan_dirs = [folder]
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/AutoExport"
    if icloud.exists():
        scan_dirs.extend([p for p in icloud.rglob("*") if p.is_dir()])

    total = 0
    files: list[str] = []
    seen: set[str] = set()
    for scan in scan_dirs:
        for path in sorted(scan.glob("*.json")):
            key = f"{path.stat().st_mtime_ns}:{path.name}"
            if key in seen:
                continue
            seen.add(key)
            try:
                n = import_health_auto_export_file(path, profile_id)
                total += n
                files.append(path.name)
            except Exception as exc:
                _log_sync("health_auto_export", "error", str(exc), 0, profile_id)

    return {"files_processed": files, "records_upserted": total, "folder": str(folder)}


def _log_sync(provider: str, status: str, message: str, records: int, profile_id: str | None) -> None:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    conn.execute(
        "INSERT INTO sync_log(provider, status, message, records_added, created_at) VALUES (?, ?, ?, ?, ?)",
        (provider, status, message, records, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_daily_metrics(
    metric_type: str | None = None,
    days: int = 30,
    profile_id: str | None = None,
) -> list[dict[str, Any]]:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    if metric_type:
        rows = conn.execute(
            """
            SELECT * FROM daily_metrics
            WHERE metric_type = ? AND metric_date >= date('now', ?)
            ORDER BY metric_date ASC
            """,
            (metric_type, f"-{days} days"),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM daily_metrics
            WHERE metric_date >= date('now', ?)
            ORDER BY metric_date ASC, metric_type ASC
            """,
            (f"-{days} days",),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_summary(profile_id: str | None = None) -> dict[str, Any]:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM daily_metrics WHERE metric_date = ? ORDER BY metric_type",
        (today,),
    ).fetchall()
    conn.close()
    by_type = {r["metric_type"]: dict(r) for r in rows}
    return {"date": today, "metrics": by_type}


def get_integration_status(profile_id: str | None = None) -> dict[str, Any]:
    ensure_wearables_tables(profile_id)
    conn = health_db.connect(profile_id)
    oura = conn.execute("SELECT updated_at FROM integration_tokens WHERE provider = 'oura'").fetchone()
    last_hae = conn.execute(
        "SELECT created_at, records_added FROM sync_log WHERE provider = 'health_auto_export' AND status = 'ok' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    count = conn.execute("SELECT COUNT(*) AS c FROM daily_metrics").fetchone()["c"]
    conn.close()
    from backend.integrations import oura_configured

    return {
        "oura_connected": oura is not None,
        "oura_configured": oura_configured(),
        "oura_last_sync": oura["updated_at"] if oura else None,
        "health_auto_export_last_sync": last_hae["created_at"] if last_hae else None,
        "daily_metrics_count": count,
        "health_auto_export_folder": str(health_root(profile_id) / "health_auto_export"),
    }
