from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.auth import get_current_user, require_staff_or_above
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.service import Service
from app.models.user import User
from app.repositories import appointment_repository
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.services.pagination import paginate_query

router = APIRouter()


@router.get("/")
def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: int = 0,
    limit: int = 100,
    filter_date: Optional[date] = Query(None, alias="date"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    client_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    sort_by: str = Query("appointment_date"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if skip:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size

    effective_tenant = tenant_id
    if current_user.primary_role != "superadmin":
        effective_tenant = current_user.tenant_id

    query = db.query(Appointment)
    if filter_date:
        query = query.filter(Appointment.appointment_date == filter_date)
    if date_from:
        query = query.filter(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.filter(Appointment.appointment_date <= date_to)
    if client_id:
        query = query.filter(Appointment.client_id == client_id)
    if effective_tenant:
        query = query.filter(Appointment.tenant_id == effective_tenant)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        query = (
            query.join(Client, Client.id == Appointment.client_id)
            .join(Service, Service.id == Appointment.service_id)
            .filter(or_(Client.full_name.ilike(term), Service.name.ilike(term)))
        )

    sortable = {
        "appointment_date": Appointment.appointment_date,
        "start_time": Appointment.start_time,
        "created_at": Appointment.created_at,
        "status": Appointment.status,
    }
    column = sortable.get(sort_by, Appointment.appointment_date)
    query = query.order_by(column.asc() if sort_order == "asc" else column.desc(), Appointment.start_time.asc())
    page_data = paginate_query(query, page, page_size)
    return {
        **page_data,
        "items": [AppointmentResponse.model_validate(item).model_dump(mode="json") for item in page_data["items"]],
    }


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    if current_user.primary_role != "superadmin" and current_user.tenant_id != appointment.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    result, error = appointment_repository.create_appointment(db, appointment)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    appt = appointment_repository.get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if current_user.primary_role != "superadmin" and appt.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return appt


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appointment: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    appt = appointment_repository.get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if current_user.primary_role != "superadmin" and appt.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    updated = appointment_repository.update_appointment(db, appointment_id, appointment)
    return updated


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appt = appointment_repository.get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if current_user.primary_role != "superadmin" and appt.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return appointment_repository.cancel_appointment(db, appointment_id)


@router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    appt = appointment_repository.get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    if current_user.primary_role != "superadmin" and appt.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return appointment_repository.complete_appointment(db, appointment_id)
