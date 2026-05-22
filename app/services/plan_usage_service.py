"""Plan usage rules for Turnix freemium tenants."""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.tenant import Tenant

FREE_PLAN_NAME = "free"
PREMIUM_PLAN_NAME = "premium"
FREE_MONTHLY_APPOINTMENT_LIMIT = 50
INTERNAL_LIMIT_MESSAGE = (
    "Has alcanzado el límite de 50 citas mensuales del plan Gratuito. "
    "Actualiza a Premium para seguir recibiendo citas este mes."
)


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    last_day = monthrange(year, month)[1]
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def _normalize_plan_name(tenant: Optional[Tenant]) -> str:
    if not tenant or not tenant.plan:
        return FREE_PLAN_NAME
    return (tenant.plan.name or FREE_PLAN_NAME).strip().lower()


def _display_plan_name(tenant: Optional[Tenant]) -> str:
    if tenant and tenant.plan and tenant.plan.display_name:
        return tenant.plan.display_name
    return "Gratuito"


def get_monthly_appointment_count(db: Session, tenant_id: int, year: int, month: int) -> int:
    """Count appointments created during a calendar month for one tenant."""
    start, end = _month_range(year, month)
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.created_at >= start,
            Appointment.created_at <= end,
        )
        .count()
    )


def get_plan_limit(tenant: Optional[Tenant]) -> Optional[int]:
    """Return the monthly appointment limit. None means unlimited."""
    plan_name = _normalize_plan_name(tenant)
    if plan_name == PREMIUM_PLAN_NAME:
        return None
    if tenant and tenant.plan and tenant.plan.max_appointments_monthly is not None:
        return int(tenant.plan.max_appointments_monthly)
    return FREE_MONTHLY_APPOINTMENT_LIMIT


def get_plan_usage_summary(
    db: Session,
    tenant_id: int,
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negocio no encontrado.")

    used = get_monthly_appointment_count(db, tenant_id, year, month)
    limit = get_plan_limit(tenant)
    remaining = None if limit is None else max(limit - used, 0)
    usage_percentage = 0 if limit in (None, 0) else min(100, round(used / limit * 100))

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "plan": _display_plan_name(tenant),
        "plan_name": _normalize_plan_name(tenant),
        "monthly_limit": limit,
        "used_this_month": used,
        "remaining_this_month": remaining,
        "usage_percentage": usage_percentage,
        "limit_reached": bool(limit is not None and used >= limit),
        "near_limit": bool(limit is not None and used >= int(limit * 0.8)),
        "year": year,
        "month": month,
    }


def can_create_appointment(db: Session, tenant_id: int) -> bool:
    summary = get_plan_usage_summary(db, tenant_id)
    return not summary["limit_reached"]


def assert_can_create_appointment(db: Session, tenant_id: int) -> None:
    summary = get_plan_usage_summary(db, tenant_id)
    if summary["limit_reached"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "PLAN_LIMIT_REACHED",
                "message": INTERNAL_LIMIT_MESSAGE,
                "usage": summary,
            },
        )

