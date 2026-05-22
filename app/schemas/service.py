from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ServiceBase(BaseModel):
    tenant_id: int
    name: str
    description: Optional[str] = None
    duration_minutes: int = 30
    price: Decimal
    is_active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

