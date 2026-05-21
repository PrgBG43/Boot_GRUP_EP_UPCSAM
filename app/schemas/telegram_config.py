from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TelegramConfigBase(BaseModel):
    welcome_message: Optional[str] = None
    services_message: Optional[str] = None
    ask_date_message: Optional[str] = None
    ask_time_message: Optional[str] = None
    confirm_message: Optional[str] = None
    cancel_message: Optional[str] = None
    unavailable_message: Optional[str] = None
    allow_cancellation: Optional[bool] = True
    show_prices: Optional[bool] = True
    show_duration: Optional[bool] = True
    use_global_bot: Optional[bool] = True
    bot_name: Optional[str] = None
    bot_description: Optional[str] = None
    bot_short_description: Optional[str] = None


class TelegramConfigUpdate(TelegramConfigBase):
    """Schema para actualizar configuración. El token se conserva solo como futuro avanzado."""

    bot_token: Optional[str] = None


class TelegramConfigResponse(TelegramConfigBase):
    id: int
    tenant_id: int
    tenant_slug: Optional[str] = None
    bot_username: Optional[str] = None
    global_bot_username: Optional[str] = None
    public_bot_link: Optional[str] = None
    bot_status: Optional[str] = "sin_configurar"
    is_active: Optional[bool] = False
    last_validated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TelegramPublicLinkResponse(BaseModel):
    bot_username: Optional[str] = None
    business_slug: Optional[str] = None
    public_link: Optional[str] = None


class TelegramValidateRequest(BaseModel):
    bot_token: str


class TelegramValidateResponse(BaseModel):
    ok: bool
    bot_username: Optional[str] = None
    bot_name: Optional[str] = None
    status: str
    message: str
