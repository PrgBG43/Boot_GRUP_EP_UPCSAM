from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationBase(BaseModel):
    tenant_id: int
    chat_id: str
    last_interaction_at: Optional[datetime] = None
    visit_count: int = 0


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    chat_id: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    visit_count: Optional[int] = None


class ConversationResponse(ConversationBase):
    id: int

    class Config:
        from_attributes = True
