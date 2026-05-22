"""Endpoints de planes freemium."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.auth import require_superadmin
from app.models.plan import Plan
from app.models.user import User

router = APIRouter()


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    max_appointments_monthly: Optional[int] = None
    max_active_services: Optional[int] = None
    max_staff: Optional[int] = None
    allows_advanced_reminders: bool
    allows_analytics: bool
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[PlanResponse])
def list_plans(db: Session = Depends(get_db)):
    return (
        db.query(Plan)
        .filter(Plan.is_active == True, Plan.name.in_(["free", "premium"]))
        .order_by(Plan.id)
        .all()
    )


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.name.in_(["free", "premium"])).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan
