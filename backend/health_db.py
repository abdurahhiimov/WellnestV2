"""SQLite storage for Wellnest health data."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.paths import REPO_ROOT, db_path, ensure_health_folders, load_profile_context


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problem_list (
    id TEXT PRIMARY KEY,
    title_ru TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    triggers TEXT,
    notes TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    generic TEXT,
    dose TEXT,
    purpose TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_code TEXT NOT NULL,
    test_name_ru TEXT NOT NULL,
    value REAL,
    value_text TEXT,
    unit TEXT,
    ref_low REAL,
    ref_high REAL,
    flag TEXT,
    sample_date TEXT NOT NULL,
    source_file TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_ru TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'planned',
    status TEXT NOT NULL DEFAULT 'open',
    due_date TEXT,
    category TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkin_date TEXT NOT NULL,
    day_score INTEGER,
    summary_ru TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_type TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    report_date TEXT NOT NULL,
    findings TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL
);
"""


# Paths whose schema has been ensured this process (avoids re-running on every connect).
_schema_ready: set[str] = set()


def connect(profile_id: str | None = None) -> sqlite3.Connection:
    ensure_health_folders(profile_id)
    path = db_path(profile_id)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Ensure the schema exists. The launcher's init_db runs before onboarding
    # (when there is no profile yet and it fails), so without this a freshly
    # onboarded install would 500 on the first query. CREATE TABLE IF NOT EXISTS
    # is idempotent; we only run it once per DB path per process.
    key = str(path)
    if key not in _schema_ready:
        conn.executescript(SCHEMA)
        _schema_ready.add(key)
    return conn


def init_db(profile_id: str | None = None) -> Path:
    conn = connect(profile_id)
    conn.executescript(SCHEMA)
    pid = profile_id or __import__("backend.paths", fromlist=["active_profile_id"]).active_profile_id()
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("profile_id", pid),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("initialized_at", datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    from backend import datapoints as dp
    from backend.wearables import ensure_wearables_tables

    dp.ensure_datapoint_tables(profile_id)
    ensure_wearables_tables(profile_id)
    _ensure_integrations_template(profile_id)
    return db_path(profile_id)


def _ensure_integrations_template(profile_id: str | None = None) -> None:
    from backend.integrations import integrations_path

    dest = integrations_path()
    if dest.exists():
        return
    example = REPO_ROOT / "profiles" / "default" / "integrations.example.json"
    if not example.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")


def seed_from_profile(profile_id: str | None = None) -> None:
    ctx = load_profile_context(profile_id)
    conn = connect(profile_id)
    now = datetime.utcnow().isoformat()

    for med in ctx.get("medications", []):
        existing = conn.execute(
            "SELECT 1 FROM medications WHERE name = ? AND status = 'active'",
            (med["name"],),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO medications(name, generic, dose, purpose, status, started_at)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (
                med["name"],
                med.get("generic"),
                med.get("dose"),
                med.get("purpose"),
                now,
            ),
        )

    default_tasks = [
        ("УЗИ малого таза", "urgent", "imaging"),
        ("УЗИ плеча", "important", "imaging"),
        ("Контроль эстрадиола", "important", "lab"),
        ("МРТ гипофиза", "important", "imaging"),
    ]
    for title, priority, category in default_tasks:
        existing = conn.execute(
            "SELECT 1 FROM tasks WHERE title_ru = ? AND status = 'open'",
            (title,),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO tasks(title_ru, priority, status, category, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (title, priority, category, now),
        )

    default_problems = [
        ("P001", "Пролактинома — контроль пролактина и МРТ", "active"),
        ("P002", "Гипотиреоз / Хашимото — контроль ТТГ", "active"),
        ("P003", "Менопауза / ЗГТ (Дивигель) — контроль эстрадиола", "active"),
    ]
    for pid_code, title, status in default_problems:
        conn.execute(
            """
            INSERT OR IGNORE INTO problem_list(id, title_ru, status, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (pid_code, title, status, now),
        )

    conn.commit()
    conn.close()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def lab_freshness(test_code: str, sample_date: str, profile_id: str | None = None) -> dict[str, Any]:
    ctx = load_profile_context(profile_id)
    windows: dict[str, int] = ctx.get("data_freshness_days", {})
    window = windows.get(test_code, windows.get("default_lab", 180))
    sd = _parse_date(sample_date)
    if not sd:
        return {"status": "unknown", "days_old": None, "window_days": window}
    days_old = (date.today() - sd).days
    if days_old <= window:
        status = "fresh"
    elif days_old <= window * 2:
        status = "aging"
    else:
        status = "stale"
    messages_ru = {
        "fresh": "данные актуальны",
        "aging": f"данные от {sample_date}, актуальность под вопросом",
        "stale": f"данные от {sample_date} — устарели для уверенных выводов",
        "unknown": "дата анализа неизвестна",
    }
    messages_en = {
        "fresh": "up to date",
        "aging": f"from {sample_date}, may be outdated",
        "stale": f"from {sample_date} — too old for confident conclusions",
        "unknown": "sample date unknown",
    }
    return {
        "status": status,
        "days_old": days_old,
        "window_days": window,
        "message_ru": messages_ru[status],
        "message_en": messages_en[status],
    }


def get_patient_profile(profile_id: str | None = None) -> dict[str, Any]:
    from backend.profile_store import load_profile
    ctx = load_profile_context(profile_id)
    full = load_profile(profile_id)
    conn = connect(profile_id)
    problems = [dict(r) for r in conn.execute("SELECT * FROM problem_list ORDER BY id")]
    conn.close()
    age = date.today().year - ctx.get("birth_year", 1970)
    return {
        "profile_id": ctx["profile_id"],
        "display_name": ctx["display_name"],
        "age": age,
        "sex": ctx.get("sex") or full.get("sex"),
        "diagnoses": ctx.get("diagnoses", []),
        "medications_summary": ctx.get("medications", []),
        "nutraceuticals_count": ctx.get("nutraceuticals_count", 0),
        "last_labs_note": ctx.get("last_labs_note"),
        "gp_persona": ctx.get("gp_persona", {}),
        "problem_list": problems,
        "health_folder": str(__import__("backend.paths", fromlist=["health_root"]).health_root(profile_id)),
        "specialist_panel": full.get("specialist_panel") or [],
    }


def get_medications(profile_id: str | None = None) -> list[dict[str, Any]]:
    conn = connect(profile_id)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM medications WHERE status = 'active' ORDER BY name"
    )]
    conn.close()
    return rows


def get_tasks(profile_id: str | None = None, status: str = "open") -> list[dict[str, Any]]:
    conn = connect(profile_id)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM tasks WHERE status = ? ORDER BY CASE priority "
        "WHEN 'urgent' THEN 0 WHEN 'important' THEN 1 ELSE 2 END, id",
        (status,),
    )]
    conn.close()
    return rows


def _normalize_task_status(status: str) -> str:
    """Map legacy DB values to UI statuses."""
    mapping = {
        "open": "not_started",
        "completed": "done",
        "dismissed": "not_started",
    }
    return mapping.get(status, status)


def get_board_tasks(profile_id: str | None = None) -> list[dict[str, Any]]:
    """All tasks on the board except deleted (includes done until user removes them)."""
    conn = connect(profile_id)
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT * FROM tasks
            WHERE status NOT IN ('deleted', 'dismissed')
            ORDER BY
              CASE status
                WHEN 'not_started' THEN 0 WHEN 'open' THEN 0
                WHEN 'in_progress' THEN 1
                WHEN 'done' THEN 2 WHEN 'completed' THEN 2
                ELSE 3
              END,
              CASE priority WHEN 'urgent' THEN 0 WHEN 'important' THEN 1 ELSE 2 END,
              id
            """
        )
    ]
    conn.close()
    for row in rows:
        row["status"] = _normalize_task_status(row.get("status") or "not_started")
    return rows


def get_active_tasks(profile_id: str | None = None) -> list[dict[str, Any]]:
    """Tasks for Today widget — not done yet."""
    return [t for t in get_board_tasks(profile_id) if t["status"] in ("not_started", "in_progress")]


def update_task_status(
    task_id: int,
    status: str,
    profile_id: str | None = None,
) -> dict[str, Any]:
    allowed = {"not_started", "in_progress", "done", "open", "completed"}
    if status not in allowed:
        return {"ok": False, "error": "invalid_status"}
    # Persist canonical statuses
    persist = {
        "open": "not_started",
        "completed": "done",
        "not_started": "not_started",
        "in_progress": "in_progress",
        "done": "done",
    }[status]
    conn = connect(profile_id)
    row = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "not_found"}
    completed_at = datetime.utcnow().isoformat() if persist == "done" else None
    conn.execute(
        "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
        (persist, completed_at, task_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "id": task_id, "status": persist}


def delete_task(task_id: int, profile_id: str | None = None) -> dict[str, Any]:
    conn = connect(profile_id)
    row = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "not_found"}
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "id": task_id}


def get_lab_results(profile_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    conn = connect(profile_id)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM lab_results ORDER BY sample_date DESC, id DESC LIMIT ?",
        (limit,),
    )]
    conn.close()
    enriched = []
    for row in rows:
        item = dict(row)
        item["freshness"] = lab_freshness(row["test_code"], row["sample_date"], profile_id)

        # Apply authoritative reference ranges (corrects rows imported with wrong LLM ranges)
        test_name_for_row = item.get("test_name_ru") or ""
        test_code_for_row = item.get("test_code") or ""
        auth_low, auth_high = _authoritative_ranges(test_name_for_row, test_code_for_row, profile_id)

        if auth_low is not None or auth_high is not None:
            # Authoritative DB has ranges for this test — use them
            ref_low, ref_high = auth_low, auth_high
        elif _classify_test(test_name_for_row) == "tb_component":
            # TB component: clear any wrong LLM-extracted ranges so gauge doesn't mislead
            ref_low, ref_high = None, None
        else:
            ref_low, ref_high = item.get("ref_low"), item.get("ref_high")

        # Recompute flag with smarter logic (corrects rows stored before upgrade)
        item["flag"] = _compute_flag(
            item.get("value"), ref_low, ref_high,
            value_text=item.get("value_text"), test_name=test_name_for_row,
        )
        # Expose corrected ranges for chart rendering
        item["ref_low"] = ref_low
        item["ref_high"] = ref_high
        enriched.append(item)
    return enriched


def dashboard_snapshot(profile_id: str | None = None) -> dict[str, Any]:
    from backend.chart_data import chart_payload
    from backend.checkins import checkin_dashboard
    from backend.explainability import help_sections, today_metric_help
    from backend.weekly_brief import build_weekly_brief
    from backend.symptom_survey import survey_config
    from backend.consilium import build_consilium_sections
    from backend.consilium_ai import consilium_status as get_consilium_status
    from backend.consilium_format import render_consilium_body_html, render_symptom_answer_html
    from backend.symptom_qa import symptom_qa_status
    from backend.wearables import get_integration_status, get_today_summary

    profile = get_patient_profile(profile_id)
    labs = get_lab_results(profile_id)
    stale_labs = [l for l in labs if l["freshness"]["status"] in ("aging", "stale")]
    today = get_today_summary(profile_id)
    metrics = today.get("metrics") or {}
    consilium_st = get_consilium_status(profile_id)
    consilium_preview = build_consilium_sections(profile_id)
    consilium_report = consilium_st.get("claude_report")
    # Main dashboard shows ONLY Claude consilium — not rule-based template
    claude_specialists = (consilium_report or {}).get("specialists") or []
    sym_qa = symptom_qa_status(profile_id)
    return {
        "profile": profile,
        "medications": get_medications(profile_id),
        "tasks_open": get_active_tasks(profile_id),
        "tasks_board": get_board_tasks(profile_id),
        "lab_results": labs,
        "alerts": {
            "stale_or_aging_labs": len(stale_labs),
            "urgent_tasks": len([t for t in get_active_tasks(profile_id) if t["priority"] == "urgent"]),
        },
        "weekly_brief": build_weekly_brief(profile_id),
        "checkins": checkin_dashboard(profile_id=profile_id),
        "symptom_survey": survey_config(),
        "consilium_preview": consilium_preview,
        "consilium_status": consilium_st,
        "consilium_html": render_consilium_body_html(claude_specialists) if claude_specialists else "",
        "consilium_preview_html": render_consilium_body_html(consilium_preview.get("specialists") or []),
        "symptom_qa": sym_qa,
        "symptom_answer_html": render_symptom_answer_html(sym_qa.get("answer") or {}),
        "charts": chart_payload(profile_id),
        "today": today,
        "today_help": {
            code: today_metric_help(code, metrics.get(code))
            for code in ("sleep_hours", "resting_hr", "steps", "readiness_score", "hrv_sdnn")
        },
        "help": help_sections(),
        "integrations": get_integration_status(profile_id),
        "server_base": "http://127.0.0.1:8787",
    }


_QUALITATIVE_NEG = frozenset(["negative", "non-reactive", "not detected", "absent", "non reactive"])
_QUALITATIVE_POS = frozenset(["positive", "reactive", "detected", "present"])
_QUALITATIVE_EQ  = frozenset(["equivocal", "indeterminate", "borderline"])

_ANTIBODY_KW = frozenset([
    "igg", "igm", "iga", "igd", "ige",
    "antibod", "ab titer", " ab ", "-ab-", "titer",
    "varicella", "measles", "rubella", "mumps", "hepatitis",
    "varabigg", "immune status", "immunity",
])

_TB_EXACT = frozenset(["nil", "tb1-nil", "tb2-nil", "mitogen-nil", "tb1", "tb2", "mitogen"])
_TB_KW = ("quantiferon", "qtf", "qtg", "tb gold", "tb1-", "tb2-", "tb-1", "tb-2")


def _authoritative_ranges(
    test_name: str,
    test_code: str,
    profile_id: str | None = None,
) -> tuple[float | None, float | None]:
    """Look up authoritative reference ranges from the curated reference DB.

    Returns (ref_low, ref_high) if found, otherwise (None, None).
    Respects patient sex for sex-specific ranges.
    """
    try:
        from backend.reference_db import resolve_test_code, lookup_lab_reference
        resolved = resolve_test_code(test_code) or resolve_test_code(test_name)
        if not resolved:
            return None, None
        ref = lookup_lab_reference(test_code=resolved)
        if not ref:
            return None, None

        sex: str | None = None
        try:
            from backend.profile_store import load_profile
            profile = load_profile(profile_id)
            raw_sex = (profile.get("sex") or "").strip().lower()
            sex = raw_sex[:1] if raw_sex else None  # 'm' or 'f'
        except Exception:
            pass

        if sex == "m" and ref.get("ref_low_m") is not None:
            return ref["ref_low_m"], ref.get("ref_high_m")
        if sex == "f" and ref.get("ref_low_f") is not None:
            return ref["ref_low_f"], ref.get("ref_high_f")
        if ref.get("ref_low") is not None or ref.get("ref_high") is not None:
            return ref.get("ref_low"), ref.get("ref_high")
        return None, None
    except Exception:
        return None, None

def _classify_test(test_name: str | None) -> str:
    """Return 'antibody', 'tb_component', or 'standard'."""
    if not test_name:
        return "standard"
    n = test_name.lower()
    # QuantiFERON panel and all its sub-components
    if n in _TB_EXACT or n.endswith("-nil"):
        return "tb_component"
    if any(kw in n for kw in _TB_KW):
        return "tb_component"
    if any(kw in n for kw in _ANTIBODY_KW):
        return "antibody"
    return "standard"


def _compute_flag(
    value: float | None,
    ref_low: float | None,
    ref_high: float | None,
    value_text: str | None = None,
    test_name: str | None = None,
) -> str | None:
    # Qualitative text results take priority over numeric logic
    if value_text:
        vt = value_text.strip().lower()
        if any(neg in vt for neg in _QUALITATIVE_NEG):
            return "neg"
        if any(pos in vt for pos in _QUALITATIVE_POS):
            return "pos"
        if any(eq in vt for eq in _QUALITATIVE_EQ):
            return "equivocal"

    kind = _classify_test(test_name)

    if kind == "tb_component":
        # TB sub-components: don't flag individually — the overall NEGATIVE/POSITIVE
        # result is what matters (captured via value_text on the parent row).
        return None

    if kind == "antibody":
        if value is None:
            return None
        # For antibody titers: above ref_low = immune, below = not immune.
        # "High" for immunity tests is always good — don't flag as high.
        threshold = ref_low if ref_low is not None else (ref_high * 0.5 if ref_high else None)
        if threshold is not None and value >= threshold:
            return "immune"
        if value > 0:
            return "immune"  # any measurable antibody = some immunity
        return "not_immune"

    # Standard quantitative
    if value is None or ref_low is None or ref_high is None:
        return None  # no flag without complete ref range
    if value < ref_low:
        return "low"
    if value > ref_high:
        return "high"
    return "normal"


def add_lab_result(
    test_name: str,
    value: float | None,
    unit: str,
    sample_date: str,
    ref_low: float | None = None,
    ref_high: float | None = None,
    value_text: str | None = None,
    source_file: str = "manual",
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Insert a single lab result; skip if exact duplicate exists."""
    conn = connect(profile_id)
    now = datetime.utcnow().isoformat()
    test_code = test_name.lower().strip().replace(" ", "_")[:40]

    # Override LLM-provided ref ranges with authoritative DB values when available
    auth_low, auth_high = _authoritative_ranges(test_name, test_code, profile_id)
    if auth_low is not None or auth_high is not None:
        ref_low, ref_high = auth_low, auth_high

    flag = _compute_flag(value, ref_low, ref_high, value_text=value_text, test_name=test_name)

    dup = conn.execute(
        "SELECT 1 FROM lab_results WHERE test_code = ? AND sample_date = ? AND value = ?",
        (test_code, sample_date, value),
    ).fetchone()
    if dup:
        conn.close()
        return {"ok": False, "error": "duplicate"}

    conn.execute(
        """
        INSERT INTO lab_results(
            test_code, test_name_ru, value, value_text, unit,
            ref_low, ref_high, flag, sample_date, source_file, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (test_code, test_name, value, value_text, unit, ref_low, ref_high, flag, sample_date, source_file, now),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "test_code": test_code, "flag": flag}


def import_lab_results_from_json(path: Path, profile_id: str | None = None) -> int:
    """Import lab rows from JSON; skip duplicates (same test_code + sample_date + value)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    conn = connect(profile_id)
    now = datetime.utcnow().isoformat()
    inserted = 0

    for row in payload.get("results", []):
        test_code = row["test_code"]
        sample_date = row["sample_date"]
        value = row.get("value")
        ref_low = row.get("ref_low")
        ref_high = row.get("ref_high")
        test_name_for_lookup = row.get("test_name_ru") or row.get("test_code", "")

        # Override LLM-extracted ref ranges with authoritative DB values when available
        auth_low, auth_high = _authoritative_ranges(test_name_for_lookup, test_code, profile_id)
        if auth_low is not None or auth_high is not None:
            ref_low, ref_high = auth_low, auth_high

        flag = _compute_flag(value, ref_low, ref_high,
                              value_text=row.get("value_text"),
                              test_name=test_name_for_lookup)

        dup = conn.execute(
            """
            SELECT 1 FROM lab_results
            WHERE test_code = ? AND sample_date = ? AND value = ?
            """,
            (test_code, sample_date, value),
        ).fetchone()
        if dup:
            continue

        conn.execute(
            """
            INSERT INTO lab_results(
                test_code, test_name_ru, value, value_text, unit,
                ref_low, ref_high, flag, sample_date, source_file, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_code,
                row["test_name_ru"],
                value,
                row.get("value_text"),
                row.get("unit"),
                ref_low,
                ref_high,
                flag,
                sample_date,
                row.get("source_file") or path.name,
                now,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


def export_dashboard_json(profile_id: str | None = None) -> Path:
    root = ensure_health_folders(profile_id)
    out = root / "data" / "dashboard.json"
    out.write_text(
        json.dumps(dashboard_snapshot(profile_id), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out
