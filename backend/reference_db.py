"""Local clinical reference database (labs, meds, guidelines, RxNorm cache)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.paths import REPO_ROOT

REFERENCE_DIR = REPO_ROOT / "data" / "reference"
SOURCE_DIR = REFERENCE_DIR / "source"
REFERENCE_DB_PATH = REFERENCE_DIR / "reference.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lab_reference (
    test_code TEXT PRIMARY KEY,
    loinc TEXT,
    test_name_ru TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS medication_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generic_en TEXT NOT NULL,
    brand_ru TEXT,
    rxcui TEXT,
    rxnorm_name TEXT,
    payload_json TEXT NOT NULL,
    UNIQUE(generic_en, brand_ru)
);

CREATE TABLE IF NOT EXISTS drug_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rxcui_a TEXT NOT NULL,
    rxcui_b TEXT NOT NULL,
    drug_a_name TEXT,
    drug_b_name TEXT,
    severity TEXT,
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(rxcui_a, rxcui_b, description)
);

CREATE TABLE IF NOT EXISTS guidelines (
    diagnosis_code TEXT PRIMARY KEY,
    icd10 TEXT,
    label_ru TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_aliases (
    alias TEXT PRIMARY KEY,
    test_code TEXT NOT NULL
);
"""


def reference_db_path() -> Path:
    return REFERENCE_DB_PATH


def reference_db_exists() -> bool:
    return REFERENCE_DB_PATH.exists()


def connect() -> sqlite3.Connection:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(REFERENCE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def _load_json(name: str) -> dict:
    path = SOURCE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Reference source missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def import_curated_sources(conn: sqlite3.Connection) -> dict[str, int]:
    """Load bundled JSON into SQLite (no network)."""
    counts: dict[str, int] = {}

    labs = _load_json("labs.json")
    for row in labs.get("tests", []):
        code = row["test_code"]
        conn.execute(
            """
            INSERT OR REPLACE INTO lab_reference(test_code, loinc, test_name_ru, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (code, row.get("loinc"), row.get("test_name_ru", code), json.dumps(row, ensure_ascii=False)),
        )
    counts["lab_reference"] = len(labs.get("tests", []))

    meds = _load_json("medications_seed.json")
    for row in meds.get("medications", []):
        conn.execute(
            """
            INSERT OR REPLACE INTO medication_reference(generic_en, brand_ru, rxcui, rxnorm_name, payload_json)
            VALUES (?, ?, NULL, NULL, ?)
            """,
            (
                row["generic_en"],
                row.get("brand_ru"),
                json.dumps(row, ensure_ascii=False),
            ),
        )
    counts["medication_reference"] = len(meds.get("medications", []))

    guides = _load_json("guidelines.json")
    for row in guides.get("diagnoses", []):
        conn.execute(
            """
            INSERT OR REPLACE INTO guidelines(diagnosis_code, icd10, label_ru, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                row["code"],
                row.get("icd10"),
                row.get("label_ru", row["code"]),
                json.dumps(row, ensure_ascii=False),
            ),
        )
    counts["guidelines"] = len(guides.get("diagnoses", []))

    aliases = _load_json("loinc_map.json").get("aliases", {})
    conn.execute("DELETE FROM test_aliases")
    for alias, code in aliases.items():
        conn.execute(
            "INSERT OR REPLACE INTO test_aliases(alias, test_code) VALUES (?, ?)",
            (alias.lower().strip(), code),
        )
    counts["test_aliases"] = len(aliases)

    ix_path = SOURCE_DIR / "interactions_seed.json"
    if ix_path.exists():
        ix_data = json.loads(ix_path.read_text(encoding="utf-8"))
        for item in ix_data.get("interactions", []):
            conn.execute(
                """
                INSERT OR IGNORE INTO drug_interactions(
                    rxcui_a, rxcui_b, drug_a_name, drug_b_name, severity, description, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("drug_a", ""),
                    item.get("drug_b", ""),
                    item.get("drug_a"),
                    item.get("drug_b"),
                    item.get("severity"),
                    item.get("description_ru", item.get("description", "")),
                    ", ".join(item.get("sources", ["curated"])),
                ),
            )
        counts["drug_interactions_curated"] = len(ix_data.get("interactions", []))

    return counts


def update_medication_rxnorm(
    conn: sqlite3.Connection,
    generic_en: str,
    brand_ru: str | None,
    rxcui: str,
    rxnorm_name: str,
    extra: dict | None = None,
) -> None:
    row = conn.execute(
        "SELECT payload_json FROM medication_reference WHERE generic_en = ? AND (brand_ru = ? OR brand_ru IS ?)",
        (generic_en, brand_ru, brand_ru),
    ).fetchone()
    payload: dict = json.loads(row["payload_json"]) if row else {"generic_en": generic_en, "brand_ru": brand_ru}
    if extra:
        payload["rxnorm"] = extra
    conn.execute(
        """
        UPDATE medication_reference
        SET rxcui = ?, rxnorm_name = ?, payload_json = ?
        WHERE generic_en = ? AND (brand_ru = ? OR (brand_ru IS NULL AND ? IS NULL))
        """,
        (rxcui, rxnorm_name, json.dumps(payload, ensure_ascii=False), generic_en, brand_ru, brand_ru),
    )


def save_interactions(conn: sqlite3.Connection, interactions: list[dict]) -> int:
    n = 0
    for item in interactions:
        conn.execute(
            """
            INSERT OR IGNORE INTO drug_interactions(
                rxcui_a, rxcui_b, drug_a_name, drug_b_name, severity, description, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["rxcui_a"],
                item["rxcui_b"],
                item.get("drug_a_name"),
                item.get("drug_b_name"),
                item.get("severity"),
                item["description"],
                item.get("source", "RxNav"),
            ),
        )
        n += 1
    return n


def finalize_meta(conn: sqlite3.Connection, rxnorm_ok: bool, interaction_count: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("built_at", datetime.utcnow().isoformat()),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("rxnorm_fetched", "yes" if rxnorm_ok else "curated_only"),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("interaction_count", str(interaction_count)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("version", "1.0"),
    )


def resolve_test_code(name_or_code: str) -> str | None:
    if not reference_db_exists():
        return None
    key = name_or_code.lower().strip()
    conn = connect()
    row = conn.execute("SELECT test_code FROM lab_reference WHERE test_code = ?", (key,)).fetchone()
    if row:
        conn.close()
        return row["test_code"]
    row = conn.execute("SELECT test_code FROM test_aliases WHERE alias = ?", (key,)).fetchone()
    conn.close()
    return row["test_code"] if row else None


def lookup_lab_reference(test_code: str | None = None, query: str | None = None) -> dict | None:
    if not reference_db_exists():
        return None
    code = test_code or (resolve_test_code(query) if query else None)
    if not code:
        return None
    conn = connect()
    row = conn.execute("SELECT * FROM lab_reference WHERE test_code = ?", (code,)).fetchone()
    conn.close()
    if not row:
        return None
    payload = json.loads(row["payload_json"])
    return {
        "test_code": row["test_code"],
        "loinc": row["loinc"],
        "test_name_ru": row["test_name_ru"],
        **payload,
    }


def list_lab_references() -> list[dict]:
    if not reference_db_exists():
        return []
    conn = connect()
    rows = conn.execute(
        "SELECT test_code, loinc, test_name_ru FROM lab_reference ORDER BY test_name_ru"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lookup_medication(name: str = "", generic: str = "") -> list[dict]:
    if not reference_db_exists():
        return []
    q = (name or generic).lower().strip()
    conn = connect()
    rows = conn.execute("SELECT * FROM medication_reference ORDER BY generic_en").fetchall()
    conn.close()
    out = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        haystack = " ".join(
            filter(
                None,
                [
                    row["generic_en"],
                    row["brand_ru"],
                    row["rxnorm_name"],
                    payload.get("brand_en"),
                    payload.get("brand_ru"),
                ],
            )
        ).lower()
        if q and q not in haystack:
            continue
        out.append(
            {
                "generic_en": row["generic_en"],
                "brand_ru": row["brand_ru"],
                "rxcui": row["rxcui"],
                "rxnorm_name": row["rxnorm_name"],
                **payload,
            }
        )
    return out


def list_medications() -> list[dict]:
    return lookup_medication(name="") if reference_db_exists() else []


def get_guidelines(diagnosis_code: str | None = None) -> list[dict]:
    if not reference_db_exists():
        return []
    conn = connect()
    if diagnosis_code:
        rows = conn.execute(
            "SELECT * FROM guidelines WHERE diagnosis_code = ?", (diagnosis_code,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM guidelines ORDER BY label_ru").fetchall()
    conn.close()
    return [
        {
            "diagnosis_code": r["diagnosis_code"],
            "icd10": r["icd10"],
            "label_ru": r["label_ru"],
            **json.loads(r["payload_json"]),
        }
        for r in rows
    ]


def get_drug_interactions(rxcui: str | None = None) -> list[dict]:
    if not reference_db_exists():
        return []
    conn = connect()
    if rxcui:
        rows = conn.execute(
            """
            SELECT * FROM drug_interactions
            WHERE rxcui_a = ? OR rxcui_b = ?
            """,
            (rxcui, rxcui),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM drug_interactions ORDER BY severity DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patient_stack_interactions() -> list[dict]:
    """Curated interactions relevant to profile medication stack."""
    if not reference_db_exists():
        return []
    from backend.paths import load_profile_context

    profile = load_profile_context()
    generics = [
        (m.get("generic") or "").lower().split()[0]
        for m in profile.get("medications", [])
        if m.get("generic")
    ]
    conn = connect()
    rows = conn.execute("SELECT * FROM drug_interactions").fetchall()
    conn.close()
    out = []
    for r in rows:
        a = (r["drug_a_name"] or r["rxcui_a"] or "").lower()
        b = (r["drug_b_name"] or r["rxcui_b"] or "").lower()
        a_match = any(g == a or g in a or a in g for g in generics)
        b_match = any(g == b or g in b or b in g for g in generics)
        if a_match and (b_match or b in ("calcium_iron_supplements",)):
            out.append(dict(r))
    return out


def enrich_lab_result(lab_row: dict) -> dict:
    """Attach reference context to a patient lab row."""
    ref = lookup_lab_reference(test_code=lab_row.get("test_code"))
    if not ref:
        return lab_row
    enriched = dict(lab_row)
    enriched["reference"] = {
        "loinc": ref.get("loinc"),
        "interpretation_ru": ref.get("interpretation_ru"),
        "therapeutic_target_hashimoto": ref.get("therapeutic_target_hashimoto"),
        "therapeutic_target_prolactinoma": ref.get("therapeutic_target_prolactinoma"),
        "therapeutic_target_hrt": ref.get("therapeutic_target_hrt"),
        "clinical_bands": ref.get("clinical_bands"),
        "sources": ref.get("sources"),
    }
    return enriched


def compare_lab_to_reference(lab_row: dict) -> dict[str, Any]:
    """Compare patient value to lab ref + clinical bands."""
    ref = lookup_lab_reference(test_code=lab_row.get("test_code"))
    value = lab_row.get("value")
    out: dict[str, Any] = {
        "test_code": lab_row.get("test_code"),
        "value": value,
        "unit": lab_row.get("unit"),
        "lab_flag": lab_row.get("flag"),
        "notes_ru": [],
    }
    if not ref or value is None:
        return out

    bands = ref.get("clinical_bands")
    if bands and lab_row.get("test_code") == "vitamin_d":
        if value < bands["deficient"]["high"]:
            out["clinical_band_ru"] = bands["deficient"]["label_ru"]
            out["notes_ru"].append(f"По Endocrine Society: {bands['deficient']['label_ru']} (<{bands['deficient']['high']} ng/mL)")
        elif value < bands["insufficient"]["high"]:
            out["clinical_band_ru"] = bands["insufficient"]["label_ru"]
            out["notes_ru"].append(f"По Endocrine Society: {bands['insufficient']['label_ru']}")

    target = ref.get("therapeutic_target_hashimoto")
    if target and lab_row.get("test_code") == "tsh":
        lo, hi = target.get("low"), target.get("high")
        if lo is not None and hi is not None:
            if value < lo:
                out["notes_ru"].append(f"Ниже частой цели при Hashimoto ({lo}–{hi} mIU/L) — обсудить дозу Эутирокса с врачом.")
            elif value > hi:
                out["notes_ru"].append(f"Выше частой цели при Hashimoto ({lo}–{hi} mIU/L) — обсудить дозу с врачом.")

    out["reference_sources"] = ref.get("sources", [])
    return out


def db_status() -> dict[str, Any]:
    if not reference_db_exists():
        return {
            "exists": False,
            "path": str(REFERENCE_DB_PATH),
            "message_ru": "Справочная база не собрана. Запустите: python scripts/download_reference_db.py",
        }
    conn = connect()
    meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta").fetchall()}
    counts = {
        "labs": conn.execute("SELECT COUNT(*) FROM lab_reference").fetchone()[0],
        "medications": conn.execute("SELECT COUNT(*) FROM medication_reference").fetchone()[0],
        "guidelines": conn.execute("SELECT COUNT(*) FROM guidelines").fetchone()[0],
        "interactions": conn.execute("SELECT COUNT(*) FROM drug_interactions").fetchone()[0],
        "aliases": conn.execute("SELECT COUNT(*) FROM test_aliases").fetchone()[0],
    }
    conn.close()
    return {
        "exists": True,
        "path": str(REFERENCE_DB_PATH),
        "meta": meta,
        "counts": counts,
        "sources_ru": [
            "Curated: labs, guidelines (ATA, Endocrine Society, NAMS, WHO)",
            "RxNorm (NLM RxNav) — идентификаторы лекарств",
            "openFDA drug labels — отрывки drug_interactions",
            "Curated stack interactions — Достинекс / Эутирокс / Дивигель",
            "LOINC codes — сопоставление анализов (subset)",
        ],
    }


def clinical_context_for_patient(profile: dict) -> dict[str, Any]:
    """Bundle reference data relevant to patient diagnoses and meds."""
    dx_codes = [d.get("code") for d in profile.get("diagnoses", [])]
    guidelines = [g for g in get_guidelines() if g.get("diagnosis_code") in dx_codes or g.get("code") in dx_codes]
    meds = []
    for m in profile.get("medications", []):
        found = lookup_medication(name=m.get("name", ""), generic=m.get("generic", ""))
        meds.extend(found if found else [{"brand_ru": m.get("name"), "generic_en": m.get("generic"), "from_profile": True}])
    return {
        "guidelines": guidelines,
        "medications_reference": meds,
        "stack_interactions": get_patient_stack_interactions(),
        "available_labs": list_lab_references(),
    }
