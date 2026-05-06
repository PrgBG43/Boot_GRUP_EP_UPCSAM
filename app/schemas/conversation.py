from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationBase(BaseModel):
    tenant_id: int
    client_id: Optional[int] = None
    chat_id: str
    channel: str = "telegram"
    status: str = "active"
    last_interaction_at: Optional[datetime] = None
    visit_count: int = 0


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    client_id: Optional[int] = None
    chat_id: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    visit_count: Optional[int] = None


class ConversationResponse(ConversationBase):
    id: int

    class Config:
        from_attributes = True
