import re
from typing import Optional

from pydantic import BaseModel, field_validator

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_RE.fullmatch(email):
            raise ValueError("Ingresa un correo electrónico válido.")
        return email


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None


class UserMeResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

