from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.repositories import appointment_repository

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
):
    return appointment_repository.list_appointments(
        db,
        skip=skip,
        limit=limit,
        filter_date=filter_date,
        client_id=client_id,
        tenant_id=tenant_id,
        status=status_filter,
    )


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db)):
    result, error = appointment_repository.create_appointment(db, appointment)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = appointment_repository.get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return appt


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int, appointment: AppointmentUpdate, db: Session = Depends(get_db)
):
    updated = appointment_repository.update_appointment(db, appointment_id, appointment)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return updated


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = appointment_repository.cancel_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return appt


@router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = appointment_repository.complete_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return appt
