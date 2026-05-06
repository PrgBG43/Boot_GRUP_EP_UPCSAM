from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_staff_or_above
from app.models.user import User
from app.repositories import appointment_repository
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate

router = APIRouter()


@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    skip: int = 0,
    limit: int = 100,
    filter_date: Optional[date] = Query(None, alias="date"),
    client_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    # Forzar tenant_id para no-superadmin
    effective_tenant = tenant_id
    if current_user.primary_role != "superadmin":
        effective_tenant = current_user.tenant_id
    return appointment_repository.list_appointments(
        db,
        skip=skip,
        limit=limit,
        filter_date=filter_date,
        client_id=client_id,
        tenant_id=effective_tenant,
        status=status_filter,
    )


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin") and \
       current_user.tenant_id != appointment.tenant_id:
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
