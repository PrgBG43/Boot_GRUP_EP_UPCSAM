from typing import Optional

from pydantic import BaseModel


class ChannelBase(BaseModel):
    tenant_id: int
    type: str
    is_active: bool = True


class ChannelCreate(ChannelBase):
    bot_token: str


class ChannelUpdate(BaseModel):
    type: Optional[str] = None
    bot_token: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelResponse(BaseModel):
    id: int
    tenant_id: int
    type: str
    bot_token_masked: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True

