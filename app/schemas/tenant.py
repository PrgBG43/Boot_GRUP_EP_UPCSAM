from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.slug import generate_slug
from app.core.validation import validate_colombian_mobile


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
    status: Optional[str] = "active"


class TenantCreate(TenantBase):
    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre comercial es obligatorio.")
        return value.strip()

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        return validate_colombian_mobile(value, required=True)

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value):
        return generate_slug(value) if value else None


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
    status: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("El nombre comercial es obligatorio.")
        return value.strip() if value is not None else value

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        return validate_colombian_mobile(value, required=False)

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value):
        return generate_slug(value) if value else value


class TenantWithAdminCreate(BaseModel):
    """Schema tipado para POST /businesses/with-admin."""

    class BusinessData(BaseModel):
        name: str
        slug: Optional[str] = None
        description: str
        phone: str
        address: str
        state_id: int
        city_id: int
        opening_time: str = "08:00"
        closing_time: str = "20:00"
        plan_id: int
        is_active: bool = True

        @field_validator("name")
        @classmethod
        def validate_name(cls, value: str) -> str:
            if not value or not value.strip():
                raise ValueError("El nombre comercial es obligatorio.")
            return value.strip()

        @field_validator("description")
        @classmethod
        def validate_description(cls, value: str) -> str:
            if not value or not value.strip():
                raise ValueError("La descripción es obligatoria.")
            return value.strip()

        @field_validator("address")
        @classmethod
        def validate_address(cls, value: str) -> str:
            if not value or not value.strip():
                raise ValueError("La dirección es obligatoria.")
            return value.strip()

        @field_validator("phone", mode="before")
        @classmethod
        def validate_phone(cls, value):
            return validate_colombian_mobile(value, required=True)

        @field_validator("slug", mode="before")
        @classmethod
        def normalize_slug(cls, value):
            return generate_slug(value) if value else None

        @model_validator(mode="after")
        def validate_required_ids(self):
            if not self.state_id:
                raise ValueError("Selecciona un departamento.")
            if not self.city_id:
                raise ValueError("Selecciona una ciudad.")
            if not self.plan_id:
                raise ValueError("Selecciona un plan.")
            if self.opening_time >= self.closing_time:
                raise ValueError("El horario de cierre debe ser posterior al de apertura.")
            return self

    class AdminData(BaseModel):
        first_name: str
        last_name: str
        email: EmailStr
        password: str = Field(min_length=8)
        confirm_password: str
        phone: Optional[str] = None

        @field_validator("first_name")
        @classmethod
        def validate_first_name(cls, value: str) -> str:
            if not value or not value.strip():
                raise ValueError("El nombre del administrador es obligatorio.")
            return value.strip()

        @field_validator("last_name")
        @classmethod
        def validate_last_name(cls, value: str) -> str:
            if not value or not value.strip():
                raise ValueError("El apellido del administrador es obligatorio.")
            return value.strip()

        @field_validator("phone", mode="before")
        @classmethod
        def validate_phone(cls, value):
            return validate_colombian_mobile(value, required=False)

        @model_validator(mode="after")
        def validate_passwords(self):
            if self.password != self.confirm_password:
                raise ValueError("Las contraseñas no coinciden.")
            return self

    business: BusinessData
    admin: AdminData


class TenantResponse(TenantBase):
    id: int
    state_name: Optional[str] = None
    city_name: Optional[str] = None
    plan: Optional[PlanInfo] = None
    owner_user: Optional[OwnerInfo] = None
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
