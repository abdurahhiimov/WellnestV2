"""Real medical evidence retrieval — free, no key.

Grounds the consilium/symptom answers in genuine literature so the model cites
real, working URLs instead of hallucinating them (the OpenEvidence value, but
with public APIs):

  * Europe PMC REST API  (https://europepmc.org)  — free, no key
  * PubMed / DOI links derived from the same results

An OpenEvidence *enterprise* slot is included but only used if the family ever
obtains institutional credentials (api.openevidence.com requires a BAA + org_id).
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from backend.integrations import load_integrations

EUROPEPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
TIMEOUT = 10.0

# Diagnoses/meds change rarely; cache the patient library so consilium
# generation doesn't redo ~10 serial Europe PMC calls every time.
_LIBRARY_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_LIBRARY_TTL = 12 * 3600.0

# Diagnosis code -> focused English query (Russian labels search poorly).
TOPIC_QUERIES: dict[str, list[str]] = {
    "prolactinoma": [
        "prolactinoma management guideline cabergoline",
        "hyperprolactinemia treatment Endocrine Society",
    ],
    "hashimoto": [
        "hypothyroidism levothyroxine dosing guideline",
        "Hashimoto thyroiditis management ATA",
    ],
    "menopause": [
        "menopausal hormone therapy guideline estradiol",
        "menopause management NAMS position statement",
    ],
}

# Generic medication -> query (for interaction / monitoring evidence).
MED_QUERIES: dict[str, str] = {
    "cabergoline": "cabergoline safety monitoring",
    "levothyroxine": "levothyroxine absorption interaction calcium iron",
    "estradiol": "transdermal estradiol cardiovascular safety",
    "progesterone": "micronized progesterone endometrial protection",
}


# ---------------------------------------------------------------- europe pmc

def _to_evidence(rec: dict, kind: str) -> dict[str, Any] | None:
    title = (rec.get("title") or "").strip().rstrip(".")
    if not title:
        return None
    doi = rec.get("doi")
    pmid = rec.get("pmid")
    source = rec.get("source")
    rec_id = rec.get("id")
    if doi:
        url = f"https://doi.org/{doi}"
    elif pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    elif source and rec_id:
        url = f"https://europepmc.org/abstract/{source}/{rec_id}"
    else:
        return None
    journal = (rec.get("journalTitle") or "").strip()
    year = (rec.get("pubYear") or "").strip()
    label = journal + (f", {year}" if year else "")
    return {
        "title": title,
        "study_url": url,
        "source_label": label or "Europe PMC",
        "kind": kind,
        "year": year,
    }


def search_europepmc(query: str, limit: int = 2) -> list[dict[str, Any]]:
    params = {
        # Title-weighted, English, syntheses preferred; default sort = relevance.
        "query": f'(TITLE:"{query}" OR {query}) AND LANG:eng',
        "format": "json",
        "pageSize": str(max(2, limit + 3)),
        "resultType": "lite",
    }
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(EUROPEPMC_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    results = (data.get("resultList") or {}).get("result") or []
    out: list[dict[str, Any]] = []
    for rec in results[:limit]:
        ev = _to_evidence(rec, kind="guideline")
        if ev:
            out.append(ev)
    return out


def _dedupe(items: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for it in items:
        key = it.get("study_url") or it.get("title", "")
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) >= cap:
            break
    return out


# ---------------------------------------------------------------- openevidence (enterprise slot)

def _openevidence_cfg() -> dict[str, Any]:
    cfg = (load_integrations().get("openevidence") or {})
    api_key = (cfg.get("api_key") or "").strip()
    return {
        "api_key": api_key,
        "org_id": (cfg.get("org_id") or "").strip(),
        "base_url": (cfg.get("base_url") or "https://api.openevidence.com").rstrip("/"),
        "enabled": bool(api_key and not api_key.startswith("YOUR_")),
    }


def search_openevidence(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Enterprise-only. No-op unless institutional credentials are configured.

    Endpoint schema is gated (BAA required); adjust the request once docs are
    available. Wrapped so a misconfiguration never breaks consilium generation.
    """
    cfg = _openevidence_cfg()
    if not cfg["enabled"]:
        return []
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    if cfg["org_id"]:
        headers["X-Organization-Id"] = cfg["org_id"]
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{cfg['base_url']}/v1/search",
                headers=headers,
                json={"query": query, "limit": limit},
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for rec in (data.get("results") or [])[:limit]:
        title = (rec.get("title") or rec.get("answer") or "").strip()
        url = rec.get("url") or rec.get("citation_url") or ""
        if title and url:
            out.append({
                "title": title,
                "study_url": url,
                "source_label": "OpenEvidence",
                "kind": "guideline",
                "year": rec.get("year", ""),
            })
    return out


# ---------------------------------------------------------------- public api

def evidence_library_for_patient(profile_id: str | None = None, cap: int = 8) -> list[dict[str, Any]]:
    """Build a library of real citations for the patient's diagnoses + meds."""
    from backend.health_db import get_patient_profile

    cache_key = f"{profile_id or 'default'}:{cap}"
    cached = _LIBRARY_CACHE.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < _LIBRARY_TTL and cached[1]:
        return cached[1]

    profile = get_patient_profile(profile_id)
    items: list[dict[str, Any]] = []

    for dx in profile.get("diagnoses", []):
        code = (dx.get("code") if isinstance(dx, dict) else str(dx)) or ""
        for q in TOPIC_QUERIES.get(code, []):
            items.extend(search_openevidence(q, limit=1))
            items.extend(search_europepmc(q, limit=1))

    for med in profile.get("medications_summary", []):
        generic = (med.get("generic") if isinstance(med, dict) else "") or ""
        first = generic.lower().split()[0] if generic else ""
        q = MED_QUERIES.get(first)
        if q:
            items.extend(search_europepmc(q, limit=1))

    result = _dedupe(items, cap)
    if result:
        _LIBRARY_CACHE[cache_key] = (time.monotonic(), result)
    return result


def evidence_library_for_query(question: str, cap: int = 4) -> list[dict[str, Any]]:
    items = search_openevidence(question, limit=2) + search_europepmc(question, limit=cap)
    return _dedupe(items, cap)


def sources_status() -> dict[str, Any]:
    return {
        "europepmc": True,  # free, always available
        "pubmed": True,
        "openevidence": _openevidence_cfg()["enabled"],
    }
