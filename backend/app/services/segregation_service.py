import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.waste import WasteCategory, WasteRule


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", text.lower()) if token}


def classify_waste(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    item_name = str(payload.get("item_name") or "")
    item_description = str(payload.get("item_description") or "")
    source_department = str(payload.get("source_department") or "")
    contamination = str(payload.get("contamination_indication") or "")
    condition = str(payload.get("condition") or "")
    quantity = float(payload.get("quantity") or 0)

    item_text = " ".join([item_name, item_description]).lower()
    text_blob = " ".join([item_name, item_description, source_department, contamination, condition]).lower()
    text_tokens = _tokenize(item_text)

    rules = db.query(WasteRule).filter(WasteRule.active.is_(True)).all()
    matches: list[tuple[WasteRule, float]] = []

    for rule in rules:
        pattern = (rule.item_pattern or rule.item_keyword or "").strip().lower()
        if not pattern:
            continue
        if not pattern or pattern in text_blob:
            score = float(rule.confidence_level)
        else:
            words = [token for token in re.split(r"[^a-z0-9]+", pattern) if token]
            if not words:
                continue
            overlap = sum(1 for word in words if word in text_tokens)
            if overlap == 0:
                continue
            score = max(0.35, float(rule.confidence_level) - (len(words) - overlap) * 0.05)
        matches.append((rule, score))

    if not matches:
        return {
            "category": "Unclassified Waste",
            "segregation_group": "Manual review required",
            "confidence": 0.15,
            "requires_human_confirmation": True,
            "guidance": "This item does not match the current demo rule set. Escalate for human review and confirm the correct segregation stream before transport.",
            "warning": "Escalate for manual confirmation and confirm the correct segregation stream before handling or disposal.",
        }

    by_category: dict[int, float] = {}
    for rule, score in matches:
        by_category[rule.category_id] = max(by_category.get(rule.category_id, 0.0), score)

    best_category_id, best_score = max(by_category.items(), key=lambda item: item[1])
    category = db.query(WasteCategory).filter(WasteCategory.id == best_category_id, WasteCategory.active.is_(True)).first()
    if category is None:
        return {
            "category": "Unclassified Waste",
            "segregation_group": "Manual review required",
            "confidence": 0.15,
            "requires_human_confirmation": True,
            "guidance": "No active category was found. Escalate for human review.",
            "warning": "Human confirmation required before handling or disposal.",
        }

    sorted_scores = sorted(by_category.values(), reverse=True)
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
    is_ambiguous = best_score < 0.8 and second_score > 0.7
    requires_human_confirmation = (
        best_score < 0.8
        or quantity <= 0
        or any(token in text_blob for token in ["unclear", "unknown", "unsure", "mixed", "uncertain"])
        or is_ambiguous
    )
    confidence = min(0.98, max(0.52, round(best_score + 0.08, 2)))
    manual_review_warning = "Escalate for manual confirmation and confirm the correct segregation stream before handling or disposal."
    if requires_human_confirmation:
        confidence = min(confidence, 0.79)

    return {
        "category": category.name,
        "segregation_group": category.segregation_group,
        "confidence": confidence,
        "requires_human_confirmation": requires_human_confirmation,
        "guidance": category.handling_guidance or "Handle according to local facility procedure and use the recommended segregation stream.",
        "warning": manual_review_warning if requires_human_confirmation else (category.warning_message or "Use caution and escalate if the waste item is uncertain or damaged."),
    }
