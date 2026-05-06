"""Endpoints de métricas y dashboard para superadmin, tenant_admin y staff."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.auth import get_current_user, require_superadmin, require_staff_or_above
from app.models.user import User
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.client import Client
from app.models.appointment import Appointment
from app.models.conversation import Conversation

router = APIRouter()


@router.get("/superadmin", summary="Dashboard global (solo superadmin)")
def superadmin_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    today = date.today()
    month_start = today.replace(day=1)

    total_tenants = db.query(func.count(Tenant.id)).scalar()
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.is_active == True).scalar()
    total_clients = db.query(func.count(Client.id)).scalar()
    total_appointments = db.query(func.count(Appointment.id)).scalar()
    appointments_this_month = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.appointment_date >= month_start)
        .scalar()
    )
    appointments_today = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.appointment_date == today)
        .scalar()
    )

    # Distribución por plan
    from app.models.plan import Plan
    plan_distribution = (
        db.query(Plan.display_name, func.count(Tenant.id))
        .outerjoin(Tenant, Tenant.plan_id == Plan.id)
        .group_by(Plan.display_name)
        .all()
    )

    # Top tenants por citas del mes
    top_tenants = (
        db.query(Tenant.name, func.count(Appointment.id).label("count"))
        .outerjoin(Appointment, Appointment.tenant_id == Tenant.id)
        .filter(Appointment.appointment_date >= month_start)
        .group_by(Tenant.name)
        .order_by(func.count(Appointment.id).desc())
        .limit(5)
        .all()
    )

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "inactive_tenants": total_tenants - active_tenants,
        "total_clients": total_clients,
        "total_appointments": total_appointments,
        "appointments_this_month": appointments_this_month,
        "appointments_today": appointments_today,
        "plan_distribution": [{"plan": p, "count": c} for p, c in plan_distribution],
        "top_tenants_month": [{"name": n, "appointments": c} for n, c in top_tenants],
    }


@router.get("/tenant", summary="Dashboard del negocio (tenant_admin/staff)")
def tenant_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
    tenant_id: Optional[int] = Query(None),
):
    # Superadmin puede consultar cualquier tenant; los demás solo el suyo
    if current_user.primary_role == "superadmin":
        tid = tenant_id
        if tid is None:
            return {"error": "Especifica tenant_id para superadmin"}
    else:
        tid = current_user.tenant_id

    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    total_services = (
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tid)
        .scalar()
    )
    active_services = (
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tid, Service.is_active == True)
        .scalar()
    )
    total_clients = (
        db.query(func.count(Client.id))
        .filter(Client.tenant_id == tid)
        .scalar()
    )
    appointments_today = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.tenant_id == tid, Appointment.appointment_date == today)
        .scalar()
    )
    appointments_week = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.tenant_id == tid, Appointment.appointment_date >= week_start)
        .scalar()
    )
    appointments_month = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.tenant_id == tid, Appointment.appointment_date >= month_start)
        .scalar()
    )
    cancelled_month = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date >= month_start,
            Appointment.status == "cancelled",
        )
        .scalar()
    )
    cancellation_rate = round((cancelled_month / appointments_month * 100) if appointments_month else 0, 1)

    # Servicio más solicitado del mes
    top_service = (
        db.query(Service.name, func.count(Appointment.id).label("count"))
        .join(Appointment, Appointment.service_id == Service.id)
        .filter(Service.tenant_id == tid, Appointment.appointment_date >= month_start)
        .group_by(Service.name)
        .order_by(func.count(Appointment.id).desc())
        .first()
    )

    # Próximas citas
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date >= today,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(5)
        .all()
    )

    # Citas por día en los últimos 7 días
    daily_counts = []
    for i in range(7):
        d = today - timedelta(days=6 - i)
        cnt = (
            db.query(func.count(Appointment.id))
            .filter(Appointment.tenant_id == tid, Appointment.appointment_date == d)
            .scalar()
        )
        daily_counts.append({"date": str(d), "count": cnt})

    # Plan info
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    plan_info = None
    if tenant and tenant.plan:
        plan_info = {
            "name": tenant.plan.name,
            "display_name": tenant.plan.display_name,
            "max_appointments_monthly": tenant.plan.max_appointments_monthly,
            "max_active_services": tenant.plan.max_active_services,
            "appointments_used_month": appointments_month,
            "services_used": active_services,
        }

    return {
        "total_services": total_services,
        "active_services": active_services,
        "total_clients": total_clients,
        "appointments_today": appointments_today,
        "appointments_week": appointments_week,
        "appointments_month": appointments_month,
        "cancellation_rate": cancellation_rate,
        "top_service": {"name": top_service[0], "count": top_service[1]} if top_service else None,
        "upcoming_appointments": [
            {
                "id": a.id,
                "date": str(a.appointment_date),
                "start_time": str(a.start_time),
                "service_id": a.service_id,
                "client_id": a.client_id,
                "status": a.status,
            }
            for a in upcoming
        ],
        "daily_chart": daily_counts,
        "plan": plan_info,
    }


@router.get("/staff", summary="Agenda del staff (personal del negocio)")
def staff_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Métricas simples para el personal: sus citas del día y próximas."""
    if current_user.primary_role not in ("staff", "tenant_admin", "superadmin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Acceso denegado")

    today = date.today()
    tid = current_user.tenant_id

    # Para staff: citas del día (todo el negocio, staff no tiene assigned_staff_id aún)
    today_appts = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date == today,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.start_time)
        .all()
    )

    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date > today,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(10)
        .all()
    )

    completed_month = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date >= today.replace(day=1),
            Appointment.status == "completed",
        )
        .scalar()
    )

    return {
        "appointments_today": len(today_appts),
        "upcoming_count": len(upcoming),
        "completed_this_month": completed_month,
        "today_appointments": [
            {
                "id": a.id,
                "date": str(a.appointment_date),
                "start_time": str(a.start_time),
                "service_id": a.service_id,
                "client_id": a.client_id,
                "status": a.status,
                "notes": a.notes,
            }
            for a in today_appts
        ],
        "upcoming_appointments": [
            {
                "id": a.id,
                "date": str(a.appointment_date),
                "start_time": str(a.start_time),
                "service_id": a.service_id,
                "client_id": a.client_id,
                "status": a.status,
            }
            for a in upcoming
        ],
    }

