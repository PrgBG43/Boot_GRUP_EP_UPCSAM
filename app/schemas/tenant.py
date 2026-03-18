from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TenantBase(BaseModel):
    name: str
    booking_url: Optional[HttpUrl] = None
    owner_user_id: int


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    booking_url: Optional[HttpUrl] = None
    owner_user_id: Optional[int] = None


class TenantResponse(TenantBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
