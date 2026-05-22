from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.availability_service import get_available_dates, get_available_slots

router = APIRouter()


@router.get("/", response_model=List[str])
def check_availability(
    tenant_id: int = Query(..., description="ID del negocio"),
    service_id: int = Query(..., description="ID del servicio"),
    target_date: date = Query(..., alias="date", description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """
    Retorna los horarios disponibles para un negocio + servicio en la fecha dada.
    Los horarios se generan cada 30 minutos dentro del horario del negocio,
    excluyendo los slots ocupados por citas existentes (no canceladas).
    """
    slots = get_available_slots(db, tenant_id, service_id, target_date)
    return slots


@router.get("/dates")
def check_available_dates(
    tenant_id: int = Query(..., description="ID del negocio"),
    service_id: int = Query(..., description="ID del servicio"),
    db: Session = Depends(get_db),
):
    """Retorna días disponibles generados según agenda, bloqueos y plan."""
    return get_available_dates(db, tenant_id, service_id)

