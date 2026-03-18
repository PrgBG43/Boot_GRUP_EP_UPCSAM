from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    person_id: int
    email: EmailStr
    password_hash: str
    is_active: bool = True


class UserCreate(UserBase):
    role_ids: Optional[List[int]] = None
    permission_ids: Optional[List[int]] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password_hash: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
    permission_ids: Optional[List[int]] = None


class UserResponse(BaseModel):
    id: int
    person_id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
