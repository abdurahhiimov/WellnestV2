"""Derive a linked medical graph from a profile (MediKeep-inspired).

Connects conditions ↔ medications ↔ labs ↔ allergies so the consilium and
symptom engine reason over relationships, not isolated facts. Links are derived
from explicit fields (medication.treats, condition.related_labs) and fall back
to heuristic matching on condition codes / medication purpose.
"""

from __future__ import annotations

from typing import Any

# Heuristic condition_code -> lab test codes, used when a condition has no
# explicit related_labs. Keeps the graph useful without manual linking.
CONDITION_LAB_HINTS: dict[str, list[str]] = {
    "hypothyroidism": ["tsh", "t4", "t3", "ft4"],
    "hashimoto": ["tsh", "t4", "ft4", "anti_tpo"],
    "hyperthyroidism": ["tsh", "ft4", "ft3"],
    "prolactinoma": ["prolactin"],
    "diabetes": ["glucose", "hba1c", "insulin"],
    "prediabetes": ["glucose", "hba1c"],
    "anemia": ["hemoglobin", "ferritin", "iron", "b12"],
    "high_cholesterol": ["cholesterol", "ldl", "hdl", "triglycerides"],
    "menopause": ["estradiol", "fsh", "lh"],
    "osteoporosis": ["vitamin_d", "calcium"],
    "vitamin_deficiency": ["vitamin_d", "b12", "ferritin"],
}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def build_medical_graph(profile: dict[str, Any]) -> dict[str, Any]:
    conditions = profile.get("conditions") or []
    medications = profile.get("medications") or []
    allergies = profile.get("allergies") or []

    nodes_by_condition: list[dict[str, Any]] = []
    for c in conditions:
        code = _norm(c.get("code"))
        label = c.get("label") or c.get("code") or ""

        # medications that treat this condition (explicit `treats` or purpose match)
        meds = []
        for m in medications:
            treats = [_norm(x) for x in (m.get("treats") or [])]
            purpose = _norm(m.get("purpose"))
            if code and (code in treats or code in purpose):
                meds.append(m.get("name"))

        related_labs = [_norm(x) for x in (c.get("related_labs") or [])]
        if not related_labs:
            related_labs = CONDITION_LAB_HINTS.get(code, [])

        nodes_by_condition.append(
            {
                "condition": label,
                "code": code,
                "treated_by": meds,
                "related_labs": related_labs,
            }
        )

    # medications not linked to any condition (orphans worth flagging)
    linked_meds = {m for n in nodes_by_condition for m in n["treated_by"]}
    unlinked_meds = [m.get("name") for m in medications if m.get("name") not in linked_meds]

    return {
        "condition_links": nodes_by_condition,
        "unlinked_medications": unlinked_meds,
        "allergies": [
            {
                "allergen": a.get("allergen"),
                "reaction": a.get("reaction"),
                "severity": a.get("severity"),
            }
            for a in allergies
            if a.get("allergen")
        ],
        "note": (
            "Use these links: only attribute a medication to the condition it treats, "
            "and read the related labs when assessing that condition. "
            "NEVER recommend anything the patient is allergic to."
        ),
    }


def allergy_summary(profile: dict[str, Any]) -> str:
    """One-line allergy string for prompt safety headers; '' if none."""
    allergies = profile.get("allergies") or []
    parts = []
    for a in allergies:
        allergen = a.get("allergen")
        if not allergen:
            continue
        sev = a.get("severity")
        parts.append(f"{allergen}" + (f" ({sev})" if sev else ""))
    return ", ".join(parts)
