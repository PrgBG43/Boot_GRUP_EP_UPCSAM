from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.support import SUPPORT_TICKET_PRIORITIES, SUPPORT_TICKET_STATUSES


class SupportTicketCreate(BaseModel):
    tenant_id: Optional[int] = None
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=4000)
    priority: str = "normal"
    category: Optional[str] = Field(default="general", max_length=80)

    @field_validator("subject", "description", "category", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in SUPPORT_TICKET_PRIORITIES:
            raise ValueError("Prioridad invalida.")
        return value


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=3, max_length=160)
    description: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=80)
    assigned_to_user_id: Optional[int] = None

    @field_validator("subject", "description", "category", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORT_TICKET_STATUSES:
            raise ValueError("Estado invalido.")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORT_TICKET_PRIORITIES:
            raise ValueError("Prioridad invalida.")
        return value


class SupportTicketMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    is_internal_note: bool = False

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("El mensaje no puede estar vacio.")
        return clean


class SupportTicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_user_id: Optional[int] = None
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    message: str
    created_at: Optional[datetime] = None
    is_internal_note: bool = False

    class Config:
        from_attributes = True


class SupportTicketResponse(BaseModel):
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    tenant_plan: Optional[str] = None
    tenant_plan_label: Optional[str] = None
    is_premium: bool = False
    created_by_user_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    subject: str
    description: str
    status: str
    priority: str
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    messages: list[SupportTicketMessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
