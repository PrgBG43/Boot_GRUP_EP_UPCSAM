from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TenantBase(BaseModel):
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    opening_time: Optional[str] = "08:00"
    closing_time: Optional[str] = "20:00"
    booking_url: Optional[str] = None
    owner_user_id: Optional[int] = None
    is_active: bool = True


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    booking_url: Optional[str] = None
    owner_user_id: Optional[int] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
