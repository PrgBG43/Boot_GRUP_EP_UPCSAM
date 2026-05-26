from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


TelegramCommandAction = Literal[
    "iniciar_agendamiento",
    "mostrar_servicios",
    "mostrar_horarios",
    "mostrar_citas_cliente",
    "cancelar_cita",
    "mostrar_ayuda",
    "respuesta_personalizada",
]


class TelegramBotCommandConfig(BaseModel):
    command: str
    description: str
    action_type: TelegramCommandAction = "respuesta_personalizada"
    message: Optional[str] = None
    is_active: bool = True


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
    cancel_start_message: Optional[str] = None
    cancel_no_appointments_message: Optional[str] = None
    cancel_select_message: Optional[str] = None
    cancel_confirm_message: Optional[str] = None
    cancel_success_message: Optional[str] = None
    cancel_rejected_message: Optional[str] = None
    cancellation_disabled_message: Optional[str] = None
    unavailable_message: Optional[str] = None
    goodbye_message: Optional[str] = None
    plan_limit_public_message: Optional[str] = None
    reminder_30_message: Optional[str] = None
    reminder_15_message: Optional[str] = None
    allow_cancellation: Optional[bool] = None
    auto_start_on_greeting: Optional[bool] = None
    show_prices: Optional[bool] = None
    show_duration: Optional[bool] = None
    collect_phone: Optional[bool] = None
    require_confirmation: Optional[bool] = None
    bot_name: Optional[str] = None
    bot_description: Optional[str] = None
    bot_short_description: Optional[str] = None
    bot_commands: Optional[Union[list[TelegramBotCommandConfig], str]] = None


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
    bot_commands: list[TelegramBotCommandConfig] = Field(default_factory=list)
    bot_token_masked: Optional[str] = None
    public_link: Optional[str] = None
    internal_logo_url: Optional[str] = None
    internal_logo_updated_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    listener_active: bool = False
    listener_status: Optional[str] = "inactive"
    listener_started_at: Optional[datetime] = None
    last_message_received_at: Optional[datetime] = None
    last_bot_error: Optional[str] = None
    welcome_message: Optional[str] = None
    services_message: Optional[str] = None
    ask_name_message: Optional[str] = None
    ask_phone_message: Optional[str] = None
    ask_service_message: Optional[str] = None
    ask_date_message: Optional[str] = None
    ask_time_message: Optional[str] = None
    confirm_message: Optional[str] = None
    cancel_message: Optional[str] = None
    cancel_start_message: Optional[str] = None
    cancel_no_appointments_message: Optional[str] = None
    cancel_select_message: Optional[str] = None
    cancel_confirm_message: Optional[str] = None
    cancel_success_message: Optional[str] = None
    cancel_rejected_message: Optional[str] = None
    cancellation_disabled_message: Optional[str] = None
    unavailable_message: Optional[str] = None
    goodbye_message: Optional[str] = None
    plan_limit_public_message: Optional[str] = None
    reminder_30_message: Optional[str] = None
    reminder_15_message: Optional[str] = None
    allow_cancellation: bool = True
    auto_start_on_greeting: bool = False
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
    listener_active: bool = False
    listener_status: Optional[str] = "inactive"
    connection_status: str
    message: str

