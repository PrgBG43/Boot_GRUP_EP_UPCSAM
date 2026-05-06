from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, field_validator

VALID_STATUSES = ("pending", "confirmed", "cancelled", "completed")


class AppointmentBase(BaseModel):
    tenant_id: int
    service_id: int
    client_id: int
    appointment_date: date
    start_time: time
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"Estado inválido. Debe ser uno de: {VALID_STATUSES}")
        return v


class AppointmentResponse(BaseModel):
    id: int
    tenant_id: int
    service_id: int
    client_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
