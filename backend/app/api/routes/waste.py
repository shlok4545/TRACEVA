from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.database import get_db
from app.models.user import User
from app.models.waste import WasteCategory, WasteRule
from app.services.risk_service import assess_risk, get_risk_config
from app.services.segregation_service import classify_waste

router = APIRouter()


@router.get("/waste-categories")
async def list_waste_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "WARD_STAFF", "REGULATOR", "COLLECTOR", "TREATMENT_FACILITY"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to waste classification data.")

    categories = db.query(WasteCategory).filter(WasteCategory.active.is_(True)).order_by(WasteCategory.id.asc()).all()
    return [
        {
            "id": category.id,
            "name": category.name,
            "code": category.code,
            "description": category.description,
            "segregation_group": category.segregation_group,
            "risk_level": category.risk_level,
            "default_disposal_method": category.default_disposal_method,
            "handling_guidance": category.handling_guidance,
            "warning_message": category.warning_message,
            "active": category.active,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
        for category in categories
    ]


@router.get("/waste-categories/{category_id}")
async def get_waste_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "WARD_STAFF", "REGULATOR", "COLLECTOR", "TREATMENT_FACILITY"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to waste classification data.")

    category = db.query(WasteCategory).filter(WasteCategory.id == category_id, WasteCategory.active.is_(True)).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste category not found.")

    return {
        "id": category.id,
        "name": category.name,
        "code": category.code,
        "description": category.description,
        "segregation_group": category.segregation_group,
        "risk_level": category.risk_level,
        "default_disposal_method": category.default_disposal_method,
        "handling_guidance": category.handling_guidance,
        "warning_message": category.warning_message,
        "active": category.active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


@router.post("/segregation/assess")
async def assess_segregation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "WARD_STAFF", "REGULATOR", "COLLECTOR", "TREATMENT_FACILITY"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to assess waste.")

    if not payload or not str(payload.get("item_name") or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="item_name is required.")
    if not str(payload.get("source_department") or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_department is required.")
    if payload.get("quantity") is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="quantity is required.")

    try:
        quantity = float(payload.get("quantity"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="quantity must be a number.") from None

    if quantity < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="quantity cannot be negative.")

    try:
        result = classify_waste(db, payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Classification failed: {exc}") from exc

    return result


@router.post("/risk/assess")
async def assess_risk_endpoint(
    payload: dict,
    db: Session = Depends(get_db),
):
    if not payload or not str(payload.get("waste_category") or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="waste_category is required.")

    try:
        result = assess_risk(db, payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Risk assessment failed: {exc}") from exc

    return result


@router.get("/risk/config")
async def get_risk_config_endpoint(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "REGULATOR", "WARD_STAFF", "COLLECTOR", "TREATMENT_FACILITY"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view risk configuration.")
    return get_risk_config()


@router.get("/waste-rules")
async def list_waste_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "WARD_STAFF", "REGULATOR", "COLLECTOR", "TREATMENT_FACILITY"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to waste rules.")

    rules = db.query(WasteRule).filter(WasteRule.active.is_(True)).order_by(WasteRule.id.asc()).all()
    return [
        {
            "id": rule.id,
            "category_id": rule.category_id,
            "item_keyword": rule.item_keyword,
            "item_pattern": rule.item_pattern,
            "confidence_level": rule.confidence_level,
            "risk_modifier": rule.risk_modifier,
            "handling_instruction": rule.handling_instruction,
            "warning": rule.warning,
            "active": rule.active,
        }
        for rule in rules
    ]
