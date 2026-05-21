from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TelegramConfigUpdate(BaseModel):
    welcome_message: Optional[str] = None
    services_message: Optional[str] = None
    ask_name_message: Optional[str] = None
    ask_phone_message: Optional[str] = None
    ask_service_message: Optional[str] = None
    ask_date_message: Optional[str] = None
    ask_time_message: Optional[str] = None
    confirm_message: Optional[str] = None
    cancel_message: Optional[str] = None
    unavailable_message: Optional[str] = None
    goodbye_message: Optional[str] = None
    allow_cancellation: Optional[bool] = None
    show_prices: Optional[bool] = None
    show_duration: Optional[bool] = None
    collect_phone: Optional[bool] = None
    require_confirmation: Optional[bool] = None
    bot_name: Optional[str] = None
    bot_description: Optional[str] = None
    bot_short_description: Optional[str] = None
    bot_commands: Optional[str] = None


class TelegramConnectRequest(BaseModel):
    bot_token: str


class TelegramConfigResponse(BaseModel):
    id: int
    tenant_id: int
    is_connected: bool = False
    connection_status: Optional[str] = "not_connected"
    bot_id: Optional[str] = None
    bot_username: Optional[str] = None
    bot_name: Optional[str] = None
    bot_description: Optional[str] = None
    bot_short_description: Optional[str] = None
    bot_commands: Optional[str] = None
    bot_token_masked: Optional[str] = None
    public_link: Optional[str] = None
    last_validated_at: Optional[datetime] = None
    welcome_message: Optional[str] = None
    services_message: Optional[str] = None
    ask_name_message: Optional[str] = None
    ask_phone_message: Optional[str] = None
    ask_service_message: Optional[str] = None
    ask_date_message: Optional[str] = None
    ask_time_message: Optional[str] = None
    confirm_message: Optional[str] = None
    cancel_message: Optional[str] = None
    unavailable_message: Optional[str] = None
    goodbye_message: Optional[str] = None
    allow_cancellation: bool = True
    show_prices: bool = True
    show_duration: bool = True
    collect_phone: bool = True
    require_confirmation: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TelegramPublicLinkResponse(BaseModel):
    is_connected: bool
    bot_username: Optional[str] = None
    public_link: Optional[str] = None


class TelegramConnectionResponse(BaseModel):
    is_connected: bool
    bot_username: Optional[str] = None
    bot_name: Optional[str] = None
    public_link: Optional[str] = None
    bot_token_masked: Optional[str] = None
    last_validated_at: Optional[datetime] = None
    connection_status: str
    message: str
