from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
