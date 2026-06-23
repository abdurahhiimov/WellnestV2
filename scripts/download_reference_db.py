#!/usr/bin/env python3
"""
Download and build local clinical reference database.

Sources:
  - Bundled curated JSON (labs, guidelines, medications) — always offline
  - RxNorm via NLM RxNav REST API (medications + drug interactions) — needs network once

Usage:
  python scripts/download_reference_db.py
  python scripts/download_reference_db.py --offline   # curated only, no RxNav
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from backend import reference_db  # noqa: E402

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
TIMEOUT = 30.0


def _get_json(client: httpx.Client, url: str) -> dict | list | None:
    try:
        r = client.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"  WARN: {url} -> {exc}")
        return None


def fetch_rxcui(client: httpx.Client, name: str) -> tuple[str | None, str | None]:
    """Return (rxcui, display_name) for ingredient name."""
    data = _get_json(client, f"{RXNAV_BASE}/rxcui.json?name={name}&search=2")
    if not data:
        return None, None
    ids = data.get("idGroup", {}).get("rxnormId") or []
    if not ids:
        return None, None
    rxcui = str(ids[0])
    props = _get_json(client, f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json")
    display = None
    if props and props.get("properties"):
        display = props["properties"].get("name")
    return rxcui, display or name



def fetch_fda_interactions(client: httpx.Client, generic_name: str) -> str | None:
    """Fetch drug_interactions excerpt from openFDA (replaces discontinued RxNav DDI API)."""
    url = (
        "https://api.fda.gov/drug/label.json"
        f"?search=openfda.generic_name:{generic_name}"
        "&limit=1"
    )
    data = _get_json(client, url)
    if not data or not isinstance(data, dict):
        return None
    results = data.get("results") or []
    if not results:
        return None
    di = results[0].get("drug_interactions")
    if isinstance(di, list) and di:
        text = di[0]
        return text[:4000] if len(text) > 4000 else text
    return None


def enrich_rxnorm(conn, offline: bool) -> tuple[bool, int]:
    if offline:
        print("Offline mode — skipping RxNav download.")
        return False, 0

    meds_path = reference_db.SOURCE_DIR / "medications_seed.json"
    meds = json.loads(meds_path.read_text(encoding="utf-8")).get("medications", [])

    rxcuis: list[str] = []
    ok = True

    with httpx.Client(follow_redirects=True) as client:
        print("Fetching RxNorm (NLM RxNav)...")
        for med in meds:
            search = med.get("rxnorm_search") or med.get("generic_en")
            print(f"  {med.get('brand_ru') or search} ({search})...")
            rxcui, display = fetch_rxcui(client, search)
            if not rxcui:
                print(f"    No RxCUI for {search}")
                ok = False
                continue
            print(f"    RxCUI {rxcui}: {display}")
            reference_db.update_medication_rxnorm(
                conn,
                generic_en=med["generic_en"],
                brand_ru=med.get("brand_ru"),
                rxcui=rxcui,
                rxnorm_name=display or search,
                extra={"rxcui": rxcui, "name": display},
            )
            fda_text = fetch_fda_interactions(client, med["generic_en"])
            if fda_text:
                row = conn.execute(
                    "SELECT payload_json FROM medication_reference WHERE generic_en = ?",
                    (med["generic_en"],),
                ).fetchone()
                if row:
                    payload = json.loads(row["payload_json"])
                    payload["fda_drug_interactions_excerpt"] = fda_text
                    conn.execute(
                        "UPDATE medication_reference SET payload_json = ? WHERE generic_en = ?",
                        (json.dumps(payload, ensure_ascii=False), med["generic_en"]),
                    )
                print(f"    openFDA interactions excerpt: {len(fda_text)} chars")
            rxcuis.append(rxcui)
            time.sleep(0.3)

        interaction_count = conn.execute("SELECT COUNT(*) FROM drug_interactions").fetchone()[0]
        print(f"  Curated + cached interactions: {interaction_count}")

    return ok, interaction_count


def build(offline: bool = False) -> Path:
    reference_db.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = reference_db.connect()
    reference_db.init_schema(conn)

    print("Loading curated reference sources...")
    counts = reference_db.import_curated_sources(conn)
    for k, v in counts.items():
        print(f"  {k}: {v}")

    rxnorm_ok, ix_count = enrich_rxnorm(conn, offline=offline)
    reference_db.finalize_meta(conn, rxnorm_ok=rxnorm_ok, interaction_count=ix_count)
    conn.commit()
    conn.close()

    print(f"\nReference DB: {reference_db.REFERENCE_DB_PATH}")
    status = reference_db.db_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return reference_db.REFERENCE_DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local clinical reference database")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use only bundled JSON (no RxNav network fetch)",
    )
    args = parser.parse_args()
    build(offline=args.offline)


if __name__ == "__main__":
    main()
