from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ClientBase(BaseModel):
    tenant_id: Optional[int] = None
    telegram_user_id: Optional[str] = None
    full_name: str
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    telegram_user_id: Optional[str] = None
    full_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

