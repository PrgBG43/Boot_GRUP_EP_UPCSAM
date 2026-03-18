from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ServiceBase(BaseModel):
    tenant_id: int
    name: str
    price: Decimal
    is_active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int

    class Config:
        from_attributes = True
