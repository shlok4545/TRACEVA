from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.waste import RiskAssessment, WasteCategory


RISK_THRESHOLDS = {
    "LOW": 34,
    "MEDIUM": 59,
    "HIGH": 79,
    "CRITICAL": 100,
}

BASE_RISKS = {
    "Infectious / Soiled Waste": 30,
    "Sharps": 42,
    "Contaminated Recyclable Plastic": 23,
    "Glass and Metal": 18,
    "Pharmaceutical Hazardous Waste": 48,
    "General Biomedical Waste": 16,
}

CONTAMINATION_MODIFIERS = {
    "none": 0,
    "low": 6,
    "moderate": 12,
    "high": 18,
    "severe": 24,
}

URGENCY_MODIFIERS = {
    "routine": 0,
    "priority": 6,
    "urgent": 12,
    "critical": 18,
}


def _priority_for_score(score: float) -> str:
    if score >= RISK_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if score >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def _normalize_contamination(value: Any) -> str:
    return str(value or "low").strip().lower()


def assess_risk(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    category_name = str(payload.get("waste_category") or "General Biomedical Waste")
    category = db.query(WasteCategory).filter(WasteCategory.name == category_name, WasteCategory.active.is_(True)).first()
    if category is None:
        category = db.query(WasteCategory).filter(WasteCategory.active.is_(True)).first()

    contamination_level = _normalize_contamination(payload.get("contamination_level"))
    quantity = float(payload.get("quantity") or 0)
    waiting_duration_hours = float(payload.get("waiting_duration_hours") or 0)
    damaged_seal = bool(payload.get("damaged_seal"))
    leakage = bool(payload.get("leakage"))
    incident_flag = bool(payload.get("incident_flag"))
    urgency = str(payload.get("urgency") or "routine").strip().lower()

    base_score = float(category.risk_level == "CRITICAL") * 8 + BASE_RISKS.get(category.name, 20)
    contamination_score = CONTAMINATION_MODIFIERS.get(contamination_level, 6)
    waiting_time_score = min(25, waiting_duration_hours * 0.8)
    quantity_score = min(20, quantity * 1.8)
    handling_condition_score = 0.0
    if damaged_seal:
        handling_condition_score += 10
    if leakage:
        handling_condition_score += 14
    if contamination_level in {"high", "severe"}:
        handling_condition_score += 8
    incident_score = 18 if incident_flag else 0
    urgency_score = URGENCY_MODIFIERS.get(urgency, 0)

    total_score = min(100.0, round(base_score + contamination_score + waiting_time_score + quantity_score + handling_condition_score + incident_score + urgency_score, 2))
    priority = _priority_for_score(total_score)

    factors: list[str] = []
    if category.risk_level in {"HIGH", "CRITICAL"}:
        factors.append("High-risk waste category")
    if waiting_duration_hours >= 12:
        factors.append("Extended waiting time")
    if quantity >= 5:
        factors.append("Large quantity")
    if damaged_seal or leakage:
        factors.append("Damaged seal or leakage")
    if incident_flag:
        factors.append("Incident-reported condition")
    if urgency in {"urgent", "critical"}:
        factors.append("Urgent handling requirement")
    if not factors:
        factors.append("Routine handling conditions")

    explanation = (
        f"Base risk for {category.name} is {base_score:.0f}; contamination contributes {contamination_score}; "
        f"waiting time adds {waiting_time_score:.0f}; quantity adds {quantity_score:.0f}; handling condition adds {handling_condition_score:.0f}; "
        f"incident risk adds {incident_score:.0f}; urgency adds {urgency_score:.0f}. Total score: {total_score:.0f} ({priority})."
    )

    record = RiskAssessment(
        category_id=category.id,
        base_score=round(base_score, 2),
        waiting_time_score=round(waiting_time_score, 2),
        quantity_score=round(quantity_score, 2),
        handling_condition_score=round(handling_condition_score, 2),
        incident_score=round(incident_score, 2),
        total_score=round(total_score, 2),
        priority=priority,
        reason=explanation,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "score": round(total_score, 2),
        "priority": priority,
        "factors": factors,
        "explanation": explanation,
        "category": category.name,
    }


def get_risk_config() -> dict[str, Any]:
    return {
        "formula": "Base Risk + Waiting Modifier + Quantity Modifier + Handling Modifier + Incident Modifier + Urgency Modifier = Final Risk",
        "thresholds": {
            "LOW": 34,
            "MEDIUM": 59,
            "HIGH": 79,
            "CRITICAL": 100,
        },
        "weights": {
            "base_risk": "Category baseline risk score",
            "waiting_modifier": "~0.8 per hour, capped at 25",
            "quantity_modifier": "~1.8 per item, capped at 20",
            "handling_modifier": "Leakage +14, damaged seal +10, acute contamination +8",
            "incident_modifier": "18 when an incident is flagged",
            "urgency_modifier": "routine 0, priority 6, urgent 12, critical 18",
        },
        "base_risk_by_category": BASE_RISKS,
    }
