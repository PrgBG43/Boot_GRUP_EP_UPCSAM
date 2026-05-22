from datetime import date, datetime, time, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.service import Service
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.plan_usage_service import assert_can_create_appointment


def list_appointments(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filter_date: Optional[date] = None,
    client_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(Appointment)
    if filter_date:
        query = query.filter(Appointment.appointment_date == filter_date)
    if client_id:
        query = query.filter(Appointment.client_id == client_id)
    if tenant_id:
        query = query.filter(Appointment.tenant_id == tenant_id)
    if status:
        query = query.filter(Appointment.status == status)
    return query.order_by(Appointment.appointment_date, Appointment.start_time).offset(skip).limit(limit).all()


def create_appointment(db: Session, appt_in: AppointmentCreate):
    assert_can_create_appointment(db, appt_in.tenant_id)

    service = db.query(Service).filter(Service.id == appt_in.service_id).first()
    if not service:
        return None, "Servicio no encontrado."
    if service.tenant_id != appt_in.tenant_id:
        return None, "El servicio no pertenece al negocio seleccionado."
    if not service.is_active:
        return None, "El servicio no está activo."

    # Calcular hora fin
    start_dt = datetime.combine(appt_in.appointment_date, appt_in.start_time)
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    end_time = end_dt.time()

    # Validar cruce de citas (status != cancelled)
    conflicting = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == appt_in.tenant_id,
            Appointment.appointment_date == appt_in.appointment_date,
            Appointment.status.notin_(["cancelled"]),
            Appointment.start_time < end_time,
            Appointment.end_time > appt_in.start_time,
        )
        .first()
    )
    if conflicting:
        return None, "No hay disponibilidad para ese horario. Seleccione otro horario."

    appointment = Appointment(
        tenant_id=appt_in.tenant_id,
        service_id=appt_in.service_id,
        client_id=appt_in.client_id,
        appointment_date=appt_in.appointment_date,
        start_time=appt_in.start_time,
        end_time=end_time,
        status="pending",
        notes=appt_in.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment, None


def get_appointment(db: Session, appointment_id: int):
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def update_appointment(db: Session, appointment_id: int, appt_in: AppointmentUpdate):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        return None
    for key, value in appt_in.model_dump(exclude_unset=True).items():
        setattr(appointment, key, value)
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, appointment_id: int):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        return None
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    return appointment


def complete_appointment(db: Session, appointment_id: int):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        return None
    appointment.status = "completed"
    db.commit()
    db.refresh(appointment)
    return appointment
