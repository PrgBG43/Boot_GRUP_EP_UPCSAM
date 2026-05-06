from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


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
    # Campos del bot propio
    bot_name: Optional[str] = None
    bot_description: Optional[str] = None
    bot_short_description: Optional[str] = None


class TelegramConfigUpdate(TelegramConfigBase):
    """Schema para actualizar configuración. El token se maneja por separado."""
    bot_token: Optional[str] = None  # token en texto plano solo en escritura


class TelegramConfigResponse(TelegramConfigBase):
    id: int
    tenant_id: int
    # SEGURIDAD: nunca devolvemos bot_token completo
    bot_token_masked: Optional[str] = None   # "123456:ABC****XYZ"
    bot_username: Optional[str] = None
    bot_status: Optional[str] = "sin_configurar"
    is_active: Optional[bool] = False
    last_validated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TelegramValidateRequest(BaseModel):
    bot_token: str


class TelegramValidateResponse(BaseModel):
    ok: bool
    bot_username: Optional[str] = None
    bot_name: Optional[str] = None
    status: str
    message: str
