from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.facility import Facility
from app.models.user import User
from app.models.ward import Ward

router = APIRouter()


@router.get("")
async def list_wards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    query = db.query(Ward)
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        if current_user.facility_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility context is required.")
        query = query.filter(Ward.facility_id == current_user.facility_id)

    wards = query.order_by(Ward.facility_id.asc(), Ward.name.asc()).all()
    rows = []
    for ward in wards:
        facility = db.query(Facility).filter(Facility.id == ward.facility_id).first()
        rows.append({
            "id": ward.id,
            "facility_id": ward.facility_id,
            "facility_name": facility.name if facility else None,
            "name": ward.name,
            "department_type": ward.department_type,
            "manager_user_id": ward.manager_user_id,
            "created_at": ward.created_at,
        })
    return {"count": len(rows), "wards": rows}
