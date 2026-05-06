from typing import Optional
from pydantic import BaseModel


class TelegramConfigBase(BaseModel):
    welcome_message: Optional[str] = None
    services_message: Optional[str] = None
    ask_date_message: Optional[str] = None
    ask_time_message: Optional[str] = None
    confirm_message: Optional[str] = None
    cancel_message: Optional[str] = None
    allow_cancellation: Optional[bool] = True
    show_prices: Optional[bool] = True
    show_duration: Optional[bool] = True
    use_global_bot: Optional[bool] = True


class TelegramConfigUpdate(TelegramConfigBase):
    pass


class TelegramConfigResponse(TelegramConfigBase):
    id: int
    tenant_id: int
    bot_token_hint: Optional[str] = None

    model_config = {"from_attributes": True}
