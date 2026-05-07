import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

# Regex para teléfonos colombianos:
# Acepta: 3001234567, +573001234567, +57 300 123 4567
_COL_PHONE_RE = re.compile(
    r"^(\+?57[\s\-]?)?[0-9]{3}[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}$"
)


def _validate_col_phone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    cleaned = v.strip()
    if cleaned and not _COL_PHONE_RE.match(cleaned):
        raise ValueError(
            "El teléfono debe tener un formato válido para Colombia "
            "(p.ej. 3001234567 o +57 300 123 4567)."
        )
    return cleaned


class PlanInfo(BaseModel):
    id: int
    name: str
    display_name: str

    class Config:
        from_attributes = True


class OwnerInfo(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        from_attributes = True


class TenantBase(BaseModel):
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state_id: Optional[int] = None
    city_id: Optional[int] = None
    slug: Optional[str] = None
    opening_time: Optional[str] = "08:00"
    closing_time: Optional[str] = "20:00"
    booking_url: Optional[str] = None
    plan_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    is_active: bool = True

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        return _validate_col_phone(v)


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state_id: Optional[int] = None
    city_id: Optional[int] = None
    slug: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    booking_url: Optional[str] = None
    plan_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        return _validate_col_phone(v)


class TenantWithAdminCreate(BaseModel):
    """Schema tipado para POST /businesses/with-admin."""
    class BusinessData(BaseModel):
        name: str
        slug: str
        description: Optional[str] = None
        phone: str
        address: str
        state_id: int
        city_id: int
        opening_time: str = "08:00"
        closing_time: str = "20:00"
        plan_id: int
        is_active: bool = True

        @field_validator("phone", mode="before")
        @classmethod
        def validate_phone(cls, v):
            return _validate_col_phone(v)

    class AdminData(BaseModel):
        first_name: str
        last_name: str
        email: str
        password: str
        confirm_password: str
        phone: Optional[str] = None

    business: BusinessData
    admin: AdminData


class TenantResponse(TenantBase):
    id: int
    state_name: Optional[str] = None
    city_name: Optional[str] = None
    plan: Optional[PlanInfo] = None
    owner_user: Optional[OwnerInfo] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
