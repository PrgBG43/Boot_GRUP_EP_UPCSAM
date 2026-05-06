"""
Servicio de disponibilidad de horarios.
Genera franjas horarias disponibles para un negocio + servicio en una fecha dada.
"""
from datetime import date, datetime, time, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.service import Service
from app.models.tenant import Tenant


def get_available_slots(
    db: Session,
    tenant_id: int,
    service_id: int,
    target_date: date,
) -> List[str]:
    """
    Retorna lista de horarios disponibles (HH:MM) para el negocio/servicio/fecha dados.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
    if not tenant:
        return []

    service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
    if not service:
        return []

    opening_str = tenant.opening_time or "08:00"
    closing_str = tenant.closing_time or "20:00"

    try:
        opening = datetime.strptime(opening_str, "%H:%M").time()
        closing = datetime.strptime(closing_str, "%H:%M").time()
    except ValueError:
        opening = time(8, 0)
        closing = time(20, 0)

    duration = timedelta(minutes=service.duration_minutes)

    # Obtener citas existentes confirmadas/pendientes del día
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_date == target_date,
            Appointment.status.notin_(["cancelled"]),
        )
        .all()
    )

    booked_ranges = [(a.start_time, a.end_time) for a in existing]

    # Generar slots cada 30 minutos dentro del horario del negocio
    slots = []
    current = datetime.combine(target_date, opening)
    closing_dt = datetime.combine(target_date, closing)

    while current + duration <= closing_dt:
        slot_start = current.time()
        slot_end = (current + duration).time()

        # Verificar que no haya conflicto con ninguna cita existente
        conflict = any(
            s < slot_end and e > slot_start
            for s, e in booked_ranges
        )

        if not conflict:
            slots.append(slot_start.strftime("%H:%M"))

        current += timedelta(minutes=30)

    return slots
