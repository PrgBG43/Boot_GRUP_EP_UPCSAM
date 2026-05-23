from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

VALID_DIRECTIONS = ("incoming", "outgoing")


class MessageBase(BaseModel):
    conversation_id: int
    direction: str
    content: str


class MessageCreate(MessageBase):
    pass


class MessageSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4096)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("El mensaje no puede estar vacio.")
        return clean


class MessageResponse(MessageBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

