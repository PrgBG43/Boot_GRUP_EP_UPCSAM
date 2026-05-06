from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    person_id: int
    tenant_id: Optional[int] = None
    password_hash: str
    role_ids: Optional[List[int]] = None
    permission_ids: Optional[List[int]] = None


class UserCreateFull(BaseModel):
    """Schema para crear usuario completo (superadmin only) con datos de persona."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    tenant_id: Optional[int] = None
    role_name: Optional[str] = None  # superadmin | tenant_admin | staff | customer


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    tenant_id: Optional[int] = None
    role_ids: Optional[List[int]] = None


class UserResponse(BaseModel):
    id: int
    person_id: int
    email: EmailStr
    is_active: bool
    tenant_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
