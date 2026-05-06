from datetime import datetime
from typing import Optional

from pydantic import BaseModel

VALID_DIRECTIONS = ("incoming", "outgoing")


class MessageBase(BaseModel):
    conversation_id: int
    direction: str
    content: str


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
