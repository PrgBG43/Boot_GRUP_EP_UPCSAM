from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.validation import validate_colombian_mobile


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
    """Schema para crear usuario completo con datos de persona."""

    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: Optional[str] = None
    first_name: str
    last_name: str
    phone: Optional[str] = None
    tenant_id: Optional[int] = None
    role_name: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre y apellido son obligatorios.")
        return value.strip()

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        return validate_colombian_mobile(value, required=False)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class UserStaffCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str
    phone: str
    tenant_id: Optional[int] = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre es obligatorio.")
        return value.strip()

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El apellido es obligatorio.")
        return value.strip()

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        return validate_colombian_mobile(value, required=True)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    confirm_password: Optional[str] = None
    is_active: Optional[bool] = None
    tenant_id: Optional[int] = None
    role_ids: Optional[List[int]] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        return validate_colombian_mobile(value, required=False)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.password is not None and self.confirm_password is not None:
            if self.password != self.confirm_password:
                raise ValueError("Las contraseñas no coinciden.")
        return self


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class UserResponse(BaseModel):
    id: int
    person_id: int
    email: EmailStr
    is_active: bool
    tenant_id: Optional[int] = None
    created_at: datetime
    role: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tenant_name: Optional[str] = None

    class Config:
        from_attributes = True
