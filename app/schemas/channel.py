from typing import Optional

from pydantic import BaseModel


class ChannelBase(BaseModel):
    tenant_id: int
    type: str
    bot_token: str
    is_active: bool = True


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    type: Optional[str] = None
    bot_token: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelResponse(ChannelBase):
    id: int

    class Config:
        from_attributes = True
