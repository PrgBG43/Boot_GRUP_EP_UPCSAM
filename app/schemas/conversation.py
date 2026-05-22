from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationBase(BaseModel):
    tenant_id: int
    client_id: Optional[int] = None
    chat_id: str
    bot_id: Optional[str] = None
    channel: str = "telegram"
    status: str = "active"
    current_step: Optional[str] = None
    context_data: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    visit_count: int = 0


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    client_id: Optional[int] = None
    chat_id: Optional[str] = None
    bot_id: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    current_step: Optional[str] = None
    context_data: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    visit_count: Optional[int] = None


class ConversationResponse(ConversationBase):
    id: int
    tenant_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True

