"""Runtime multi-bot de Telegram para Turnix.

Uso:
  python -m app.bot.telegram_bot

Cada tenant conecta su propio bot desde el panel. Este runtime local usa polling
para iniciar una instancia de Telegram por cada configuración conectada.
"""
import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import Conflict, InvalidToken, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.core.database import SessionLocal, create_tables
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.service import Service
from app.models.telegram_config import TelegramConfig
from app.models.tenant import Tenant
from app.repositories import appointment_repository
from app.schemas.appointment import AppointmentCreate
from app.services.availability_service import format_date_label, format_time_label, get_available_dates, get_available_slots
from app.services.bot_message_renderer import build_bot_message_context, render_bot_message
from app.services.plan_usage_service import INTERNAL_LIMIT_MESSAGE, can_create_appointment
from app.services.telegram_token_service import decrypt_token

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

ASK_NAME, ASK_PHONE, SELECT_SERVICE, SELECT_DATE, SELECT_TIME, CONFIRM_APPOINTMENT, CANCEL_SELECT_APPOINTMENT, CANCEL_CONFIRM_APPOINTMENT = range(8)

NO_SERVICES_MESSAGE = "Este negocio aún no tiene servicios disponibles para agendar."
CANCEL_START_MESSAGE = "Voy a ayudarte a cancelar una cita."
CANCEL_NO_APPOINTMENTS_MESSAGE = (
    "No encontré citas activas para cancelar. "
    "Si necesitas ayuda, comunícate directamente con el negocio."
)
CANCEL_SELECT_MESSAGE = "Encontré varias citas activas. Selecciona cuál deseas cancelar."
CANCEL_CONFIRM_MESSAGE = "¿Confirmas que deseas cancelar la cita de {service_name} del {date} a las {time}?"
CANCEL_SUCCESS_MESSAGE = "Tu cita fue cancelada correctamente."
CANCEL_REJECTED_MESSAGE = "Perfecto, tu cita se mantiene activa."
CANCELLATION_DISABLED_MESSAGE = (
    "Este negocio no tiene habilitada la cancelación por Telegram. "
    "Comunícate directamente con el establecimiento para recibir ayuda."
)
CANCEL_CONFIRM_YES = "Sí, cancelar cita"
CANCEL_CONFIRM_NO = "No, conservar cita"
DEFAULT_COMMANDS: list[dict[str, Any]] = [
    {
        "command": "/start",
        "description": "Inicia el proceso de agendamiento.",
        "action_type": "iniciar_agendamiento",
        "message": "Hola. Bienvenido a {business_name}. Vamos a agendar tu cita.",
        "is_active": True,
    },
    {
        "command": "/servicios",
        "description": "Muestra los servicios activos del negocio.",
        "action_type": "mostrar_servicios",
        "message": "Estos son nuestros servicios disponibles:",
        "is_active": True,
    },
    {
        "command": "/horarios",
        "description": "Muestra fechas u horarios disponibles.",
        "action_type": "mostrar_horarios",
        "message": "Estos son los próximos horarios disponibles:",
        "is_active": True,
    },
    {
        "command": "/citas",
        "description": "Permite consultar citas del cliente.",
        "action_type": "mostrar_citas_cliente",
        "message": None,
        "is_active": True,
    },
    {
        "command": "/cancelar",
        "description": "Permite cancelar una cita si el negocio lo permite.",
        "action_type": "cancelar_cita",
        "message": "Vamos a revisar tus citas activas para cancelar la que elijas.",
        "is_active": True,
    },
    {
        "command": "/ayuda",
        "description": "Muestra instrucciones de uso del bot.",
        "action_type": "mostrar_ayuda",
        "message": "Puedes escribir /servicios para ver nuestros servicios o /start para agendar una cita.",
        "is_active": True,
    },
]
ALLOWED_COMMAND_ACTIONS = {
    "iniciar_agendamiento",
    "mostrar_servicios",
    "mostrar_horarios",
    "mostrar_citas_cliente",
    "cancelar_cita",
    "mostrar_ayuda",
    "respuesta_personalizada",
}
GREETING_WORDS = {"hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "hey"}
GREETING_RESPONSE = (
    "Hola. Bienvenido a {business_name}. Puedes usar /start para agendar una cita "
    "o /servicios para ver nuestros servicios."
)
UNKNOWN_MESSAGE = "No entendí tu mensaje. Puedes usar /start para agendar una cita o /ayuda para ver las opciones disponibles."
CONFLICT_MESSAGE = "Este bot ya está siendo escuchado por otro proceso. Cierra el proceso anterior o reinicia el backend."


def _format_message(template: Optional[str], values: dict[str, Any]) -> str:
    return render_bot_message(template, values)


def _normalize_command_name(command: str) -> str:
    clean = (command or "").split("@", 1)[0].strip().lower()
    clean = clean if clean.startswith("/") else f"/{clean}"
    return re.sub(r"[^/a-z0-9_]", "", clean)


def _command_from_dict(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    command = _normalize_command_name(str(item.get("command") or ""))
    if not command or command == "/":
        return None
    action_type = item.get("action_type") or "respuesta_personalizada"
    if action_type not in ALLOWED_COMMAND_ACTIONS:
        action_type = "respuesta_personalizada"
    return {
        "command": command,
        "description": (item.get("description") or command.lstrip("/")).strip(),
        "action_type": action_type,
        "message": (item.get("message") or "").strip() or None,
        "is_active": bool(item.get("is_active", True)),
    }


def _commands_from_text(raw: str) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for line in raw.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if " - " in clean:
            command, description = clean.split(" - ", 1)
        elif ":" in clean:
            command, description = clean.split(":", 1)
        else:
            command, description = clean, clean.lstrip("/")
        commands.append(
            {
                "command": _normalize_command_name(command),
                "description": description.strip(),
                "action_type": "respuesta_personalizada",
                "message": None,
                "is_active": True,
            }
        )
    return commands


def _command_configs(config: TelegramConfig) -> list[dict[str, Any]]:
    raw = config.bot_commands if config else None
    if not raw:
        return [dict(item) for item in DEFAULT_COMMANDS]
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        parsed = _commands_from_text(raw)
    commands: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in parsed or []:
        data = _command_from_dict(item if isinstance(item, dict) else {})
        if not data or data["command"] in seen:
            continue
        seen.add(data["command"])
        commands.append(data)
    for item in DEFAULT_COMMANDS:
        if item["command"] not in seen:
            seen.add(item["command"])
            commands.append(dict(item))
    return commands or [dict(item) for item in DEFAULT_COMMANDS]


def _find_command(config: TelegramConfig, command: str) -> Optional[dict[str, Any]]:
    normalized = _normalize_command_name(command)
    for item in _command_configs(config):
        if item["command"] == normalized and item.get("is_active", True):
            return item
    return None


def _is_greeting(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip().lower())
    return clean in GREETING_WORDS


def _safe_error_message(exc: BaseException | str) -> str:
    message = str(exc)
    return re.sub(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b", "[token oculto]", message)


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_config_runtime_status(
    tenant_id: int,
    *,
    listener_status: Optional[str] = None,
    listener_started_at: Optional[datetime] = None,
    last_message_received_at: Optional[datetime] = None,
    last_bot_error: Optional[str] = None,
    clear_error: bool = False,
    connection_status: Optional[str] = None,
) -> None:
    db = SessionLocal()
    try:
        config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant_id).first()
        if not config:
            return
        if listener_status is not None:
            config.listener_status = listener_status
        if listener_started_at is not None:
            config.listener_started_at = listener_started_at
        if last_message_received_at is not None:
            config.last_message_received_at = last_message_received_at
        if clear_error:
            config.last_bot_error = None
        elif last_bot_error is not None:
            config.last_bot_error = last_bot_error[:1000]
        if connection_status is not None:
            config.connection_status = connection_status
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[Telegram] No se pudo actualizar el diagnóstico del bot para tenant %s", tenant_id)
    finally:
        db.close()


def _tenant_info(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    return {
        "tenant_id": context.application.bot_data["tenant_id"],
        "tenant_name": context.application.bot_data["tenant_name"],
        "bot_id": context.application.bot_data.get("bot_id"),
    }


def _get_config(db, tenant_id: int) -> TelegramConfig:
    return db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant_id).first()


def _active_services(db, tenant_id: int) -> list[Service]:
    return (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.is_active == True)
        .order_by(Service.name)
        .all()
    )


def _service_line(service: Service, config: TelegramConfig, index: int) -> str:
    parts = [f"{index}. {service.name}"]
    if config.show_duration:
        parts.append(f"{service.duration_minutes} min")
    if config.show_prices:
        parts.append(f"${int(service.price):,}")
    line = " - ".join(parts)
    if service.description:
        line += f"\n  {service.description}"
    return line


def _service_button_label(service: Service, config: TelegramConfig, index: int) -> str:
    parts = [f"{index}. {service.name}"]
    if config.show_duration:
        parts.append(f"{service.duration_minutes} min")
    if config.show_prices:
        parts.append(f"${int(service.price):,}")
    return " - ".join(parts)


def _keyboard(items: list[str], columns: int = 2) -> ReplyKeyboardMarkup:
    rows = [items[i:i + columns] for i in range(0, len(items), columns)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _client_needs_name(client: Client) -> bool:
    return not client.full_name or client.full_name.strip() in {"Cliente Telegram", "Telegram"}


def _variables(
    tenant: Tenant,
    config: TelegramConfig,
    client: Optional[Client] = None,
    service: Optional[Service] = None,
    extra=None,
    appointment: Optional[Appointment] = None,
):
    return build_bot_message_context(
        tenant=tenant,
        config=config,
        client=client,
        service=service,
        appointment=appointment,
        extra=extra,
    )


def _config_message(config: TelegramConfig, key: str, default: str) -> str:
    return getattr(config, key, None) or default


def _cancel_appointment_extra(appointment: Appointment) -> dict[str, Any]:
    return {
        "date": format_date_label(appointment.appointment_date),
        "time": format_time_label(appointment.start_time.strftime("%H:%M")),
        "appointment_status": appointment.status,
    }


def _cancel_appointment_values(
    tenant: Tenant,
    config: TelegramConfig,
    client: Client,
    appointment: Appointment,
):
    service = appointment.service if getattr(appointment, "service", None) else None
    return service, _variables(
        tenant,
        config,
        client,
        service,
        extra=_cancel_appointment_extra(appointment),
        appointment=appointment,
    )


def _cancel_appointment_label(appointment: Appointment) -> str:
    return appointment_repository.format_appointment_for_client(appointment)


def _build_cancel_options(appointments: list[Appointment]) -> tuple[list[str], dict[str, int]]:
    labels: list[str] = []
    label_counts: dict[str, int] = {}
    options: dict[str, int] = {}
    for appointment in appointments:
        base_label = _cancel_appointment_label(appointment)
        label_counts[base_label] = label_counts.get(base_label, 0) + 1
        label = base_label if label_counts[base_label] == 1 else f"{base_label} ({label_counts[base_label]})"
        labels.append(label)
        options[label] = appointment.id
    return labels, options


def _cancel_confirm_keyboard() -> ReplyKeyboardMarkup:
    return _keyboard([CANCEL_CONFIRM_YES, CANCEL_CONFIRM_NO], columns=1)


def _is_cancel_confirmation(text: str) -> bool:
    clean = (text or "").strip().lower()
    return clean in {
        "si",
        "sí",
        "yes",
        "s",
        "y",
        CANCEL_CONFIRM_YES.lower(),
    }


def _is_cancel_rejection(text: str) -> bool:
    clean = (text or "").strip().lower()
    return clean in {
        "no",
        "n",
        CANCEL_CONFIRM_NO.lower(),
    }


def _get_or_create_client(db, update: Update, tenant_id: int) -> Client:
    tg_user = update.effective_user
    full_name = (tg_user.full_name or "").strip() or "Cliente Telegram"
    client = (
        db.query(Client)
        .filter(Client.tenant_id == tenant_id, Client.telegram_user_id == str(tg_user.id))
        .first()
    )
    if not client:
        client = Client(
            tenant_id=tenant_id,
            telegram_user_id=str(tg_user.id),
            full_name=full_name,
            username=tg_user.username,
        )
        db.add(client)
    else:
        client.username = tg_user.username
        if not client.full_name:
            client.full_name = full_name
    db.flush()
    return client


def _get_or_create_conversation(db, client: Client, update: Update, tenant_id: int, bot_id: Optional[str]) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == tenant_id,
            Conversation.client_id == client.id,
            Conversation.chat_id == str(update.effective_chat.id),
            Conversation.bot_id == bot_id,
        )
        .first()
    )
    if not conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            client_id=client.id,
            chat_id=str(update.effective_chat.id),
            bot_id=bot_id,
            channel="telegram",
            status="active",
            visit_count=1,
        )
        db.add(conversation)
    else:
        conversation.visit_count = (conversation.visit_count or 0) + 1
        conversation.last_interaction_at = datetime.now(timezone.utc)
    db.flush()
    return conversation


def _save_message(conversation_id: Optional[int], direction: str, content: str) -> None:
    if not conversation_id or not content:
        return
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.last_interaction_at = datetime.now(timezone.utc)
            if direction == "incoming":
                config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == conversation.tenant_id).first()
                if config:
                    config.last_message_received_at = datetime.now(timezone.utc)
        db.add(Message(conversation_id=conversation_id, direction=direction, content=content))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("No se pudo guardar mensaje de Telegram")
    finally:
        db.close()


def _set_conversation_step(conversation_id: Optional[int], step: str, data: Optional[dict[str, Any]] = None) -> None:
    if not conversation_id:
        return
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.current_step = step
            conversation.context_data = json.dumps(data or {}, default=str)
            conversation.last_interaction_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


async def _reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs) -> None:
    try:
        await update.effective_message.reply_text(text, **kwargs)
        _save_message(context.user_data.get("conversation_id"), "outgoing", text)
        logger.info(
            "[Telegram] Respuesta enviada a chat %s para tenant %s",
            update.effective_chat.id if update.effective_chat else "desconocido",
            context.user_data.get("tenant_id") or context.application.bot_data.get("tenant_id"),
        )
    except TelegramError as exc:
        tenant_id = context.user_data.get("tenant_id") or context.application.bot_data.get("tenant_id")
        message = _safe_error_message(exc)
        if tenant_id:
            _set_config_runtime_status(tenant_id, listener_status="error", last_bot_error=message)
        logger.error("[Telegram] Error enviando respuesta para tenant %s: %s", tenant_id, message)
        raise


def _bootstrap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = _tenant_info(context)
    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.id == info["tenant_id"], Tenant.is_active == True).first()
    if not tenant:
        db.close()
        return None
    config = _get_config(db, tenant.id)
    if not config:
        config = TelegramConfig(tenant_id=tenant.id)
        db.add(config)
        db.flush()
    client = _get_or_create_client(db, update, tenant.id)
    conversation = _get_or_create_conversation(db, client, update, tenant.id, info.get("bot_id"))
    db.commit()
    db.refresh(client)
    db.refresh(conversation)
    username = update.effective_user.username if update.effective_user else None
    logger.info("[Telegram] Mensaje recibido de @%s para tenant %s", username or client.telegram_user_id or "usuario", tenant.id)
    context.user_data.update(
        {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "bot_id": info.get("bot_id"),
            "client_id": client.id,
            "conversation_id": conversation.id,
        }
    )
    return db, tenant, config, client, conversation


async def _show_services(update: Update, context: ContextTypes.DEFAULT_TYPE, db, tenant: Tenant, config: TelegramConfig) -> int:
    services = _active_services(db, tenant.id)
    if not services:
        await _reply(update, context, NO_SERVICES_MESSAGE, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(context.user_data.get("conversation_id"), "COMPLETED")
        return ConversationHandler.END

    labels = [_service_button_label(service, config, i + 1) for i, service in enumerate(services)]
    services_map = {str(i + 1): service.id for i, service in enumerate(services)}
    services_map.update({label: service.id for label, service in zip(labels, services)})
    context.user_data["services_list"] = services_map
    lines = [
        _format_message(config.services_message or "Estos son nuestros servicios disponibles:", _variables(tenant, config)),
        _format_message(config.ask_service_message or "Selecciona el servicio que deseas agendar.", _variables(tenant, config)),
    ]
    lines.extend(_service_line(service, config, i + 1) for i, service in enumerate(services))
    await _reply(update, context, "\n".join(lines), reply_markup=_keyboard(labels, columns=1))
    _set_conversation_step(
        context.user_data.get("conversation_id"),
        "SELECT_SERVICE",
        {"services": context.user_data["services_list"]},
    )
    return SELECT_SERVICE


async def _show_services_readonly(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    tenant: Tenant,
    config: TelegramConfig,
    custom_message: Optional[str] = None,
) -> int:
    services = _active_services(db, tenant.id)
    if not services:
        await _reply(update, context, NO_SERVICES_MESSAGE, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(context.user_data.get("conversation_id"), "COMPLETED")
        return ConversationHandler.END

    lines = [
        _format_message(
            custom_message or config.services_message or "Estos son nuestros servicios disponibles:",
            _variables(tenant, config),
        )
    ]
    lines.extend(_service_line(service, config, i + 1) for i, service in enumerate(services))
    lines.append("Escribe /start cuando quieras agendar una cita.")
    await _reply(update, context, "\n".join(lines), reply_markup=ReplyKeyboardRemove())
    _set_conversation_step(context.user_data.get("conversation_id"), "SERVICES_SHOWN")
    return ConversationHandler.END


async def _show_available_schedule(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    tenant: Tenant,
    config: TelegramConfig,
    custom_message: Optional[str] = None,
) -> int:
    services = _active_services(db, tenant.id)
    if not services:
        await _reply(update, context, NO_SERVICES_MESSAGE, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    lines = [
        _format_message(
            custom_message or "Estos son los próximos horarios disponibles:",
            _variables(tenant, config),
        )
    ]
    for service in services[:5]:
        dates = get_available_dates(db, tenant.id, service.id)
        labels = [item["label"] for item in dates[:3]]
        if labels:
            lines.append(f"{service.name}: {', '.join(labels)}")
        else:
            lines.append(f"{service.name}: sin horarios disponibles por ahora")
    lines.append("Escribe /start para elegir servicio, fecha y hora.")
    await _reply(update, context, "\n".join(lines), reply_markup=ReplyKeyboardRemove())
    _set_conversation_step(context.user_data.get("conversation_id"), "SCHEDULE_SHOWN")
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        await update.effective_message.reply_text("Este negocio no está activo en Turnix.")
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/start")
        command_config = _find_command(config, "/start")
        welcome = _format_message(command_config.get("message") if command_config else config.welcome_message, _variables(tenant, config, client))
        if not welcome:
            welcome = _format_message(config.welcome_message, _variables(tenant, config, client))
        await _reply(update, context, welcome)
        return await _show_services(update, context, db, tenant, config)
    finally:
        db.close()


async def _continue_after_contact_details(update: Update, context: ContextTypes.DEFAULT_TYPE, db, tenant: Tenant, config: TelegramConfig) -> int:
    service = db.query(Service).filter(Service.id == context.user_data["selected_service_id"]).first()
    selected_time = context.user_data["selected_time"]
    if not config.require_confirmation:
        return await _create_appointment(update, context, db, config)

    end_time = (datetime.strptime(selected_time, "%H:%M") + timedelta(minutes=service.duration_minutes)).strftime("%H:%M")
    summary = (
        "Resumen de tu cita:\n"
        f"Servicio: {service.name}\n"
        f"Fecha: {format_date_label(context.user_data['selected_date'])}\n"
        f"Hora: {format_time_label(selected_time)} - {format_time_label(end_time)}\n"
        "Responde SI para confirmar o NO para cancelar."
    )
    await _reply(update, context, summary, reply_markup=ReplyKeyboardMarkup([["SI", "NO"]], resize_keyboard=True, one_time_keyboard=True))
    _set_conversation_step(
        context.user_data.get("conversation_id"),
        "CONFIRM_APPOINTMENT",
        {"service_id": service.id, "date": str(context.user_data["selected_date"]), "time": selected_time},
    )
    return CONFIRM_APPOINTMENT


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        config = _get_config(db, tenant.id)
        client.full_name = text
        db.commit()
        if config.collect_phone and not client.phone:
            await _reply(update, context, config.ask_phone_message or "Escribe tu número de celular para confirmar la cita.")
            _set_conversation_step(context.user_data.get("conversation_id"), "ASK_PHONE", {"client_name": text})
            return ASK_PHONE
        if context.user_data.get("selected_time"):
            return await _continue_after_contact_details(update, context, db, tenant, config)
        return await _show_services(update, context, db, tenant, config)
    finally:
        db.close()


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        config = _get_config(db, tenant.id)
        client.phone = text
        db.commit()
        if context.user_data.get("selected_time"):
            return await _continue_after_contact_details(update, context, db, tenant, config)
        return await _show_services(update, context, db, tenant, config)
    finally:
        db.close()


async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    service_id = context.user_data.get("services_list", {}).get(text)
    if not service_id:
        await _reply(update, context, "Escribe el número del servicio de la lista.")
        return SELECT_SERVICE

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        config = _get_config(db, tenant.id)
        service = db.query(Service).filter(Service.id == service_id, Service.tenant_id == tenant.id, Service.is_active == True).first()
        if not service:
            await _reply(update, context, "El servicio seleccionado ya no está disponible.")
            return await _show_services(update, context, db, tenant, config)

        context.user_data.update(
            {
                "selected_service_id": service.id,
                "selected_service_name": service.name,
                "selected_service_duration": service.duration_minutes,
                "selected_service_price": int(service.price),
            }
        )
        dates = get_available_dates(db, tenant.id, service.id)
        if not dates:
            message = config.plan_limit_public_message if not can_create_appointment(db, tenant.id) else config.unavailable_message
            await _reply(
                update,
                context,
                _format_message(
                    message
                    or "En este momento no hay horarios disponibles para agendar por este medio. Intenta más tarde o comunícate directamente con el establecimiento.",
                    _variables(tenant, config, service=service),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            _set_conversation_step(context.user_data.get("conversation_id"), "NO_AVAILABILITY", {"service_id": service.id})
            return ConversationHandler.END

        date_labels = [item["label"] for item in dates]
        date_map = {item["label"]: item["date"] for item in dates}
        date_map.update({str(i + 1): item["date"] for i, item in enumerate(dates)})
        context.user_data["dates_map"] = date_map
        lines = [_format_message(config.ask_date_message or "¿Cuándo quieres agendar tu cita?", _variables(tenant, config, service=service))]
        lines.extend(f"{i + 1}. {item['label']}" for i, item in enumerate(dates))
        await _reply(update, context, "\n".join(lines), reply_markup=_keyboard(date_labels, columns=2))
        _set_conversation_step(context.user_data.get("conversation_id"), "SELECT_DATE", {"service_id": service.id, "dates": date_map})
        return SELECT_DATE
    finally:
        db.close()


async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    selected_date = context.user_data.get("dates_map", {}).get(text)
    if not selected_date:
        try:
            selected_date = datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            await _reply(update, context, "Selecciona una de las fechas disponibles.")
            return SELECT_DATE
    try:
        target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        await _reply(update, context, "Selecciona una de las fechas disponibles.")
        return SELECT_DATE

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        config = _get_config(db, tenant.id)
        service = db.query(Service).filter(Service.id == context.user_data["selected_service_id"]).first()
        slots = get_available_slots(db, tenant.id, service.id, target_date)
        if not slots:
            await _reply(update, context, _format_message(config.unavailable_message, _variables(tenant, config, service=service, extra={"date": target_date})))
            return SELECT_DATE
        context.user_data["selected_date"] = target_date
        slot_labels = [format_time_label(slot) for slot in slots]
        slots_map = {str(i + 1): slot for i, slot in enumerate(slots)}
        slots_map.update({label: slot for label, slot in zip(slot_labels, slots)})
        context.user_data["slots_map"] = slots_map
        lines = [_format_message(config.ask_time_message, _variables(tenant, config, service=service, extra={"date": target_date}))]
        lines.extend(f"{i + 1}. {label}" for i, label in enumerate(slot_labels))
        await _reply(update, context, "\n".join(lines), reply_markup=_keyboard(slot_labels, columns=2))
        _set_conversation_step(
            context.user_data.get("conversation_id"),
            "SELECT_TIME",
            {"service_id": service.id, "date": str(target_date), "slots": context.user_data["slots_map"]},
        )
        return SELECT_TIME
    finally:
        db.close()


async def _create_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE, db, config: TelegramConfig) -> int:
    tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
    client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
    service = db.query(Service).filter(Service.id == context.user_data["selected_service_id"]).first()
    selected_time = context.user_data["selected_time"]

    try:
        appointment, error = appointment_repository.create_appointment(
            db,
            AppointmentCreate(
                tenant_id=tenant.id,
                service_id=service.id,
                client_id=client.id,
                appointment_date=context.user_data["selected_date"],
                start_time=datetime.strptime(selected_time, "%H:%M").time(),
                notes="Cita creada desde Telegram",
            ),
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "PLAN_LIMIT_REACHED":
            logger.warning("El negocio %s alcanzó el límite mensual del plan Gratuito.", tenant.name)
            public_message = config.plan_limit_public_message or (
                "En este momento el negocio no está disponible para recibir nuevas citas por este medio. "
                "Intenta más tarde o comunícate directamente con el establecimiento."
            )
            await _reply(update, context, _format_message(public_message, _variables(tenant, config, client, service)))
            _set_conversation_step(
                context.user_data.get("conversation_id"),
                "PLAN_LIMIT_REACHED",
                {"internal_message": INTERNAL_LIMIT_MESSAGE},
            )
            return ConversationHandler.END
        raise
    if error:
        await _reply(update, context, _format_message(config.unavailable_message, _variables(tenant, config, client, service)))
        return SELECT_DATE

    appointment.status = "confirmed"
    db.commit()
    values = _variables(
        tenant,
        config,
        client,
        service,
        {"date": context.user_data["selected_date"], "time": selected_time, "appointment_status": appointment.status},
        appointment=appointment,
    )
    await _reply(update, context, _format_message(config.confirm_message, values))
    if config.goodbye_message:
        await _reply(update, context, _format_message(config.goodbye_message, values))
    _set_conversation_step(context.user_data.get("conversation_id"), "COMPLETED", {"appointment_id": appointment.id})
    return ConversationHandler.END


async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    selected_time = context.user_data.get("slots_map", {}).get(text)
    if not selected_time:
        await _reply(update, context, "Escribe el número del horario de la lista.")
        return SELECT_TIME
    context.user_data["selected_time"] = selected_time

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        config = _get_config(db, tenant.id)
        service = db.query(Service).filter(Service.id == context.user_data["selected_service_id"]).first()
        client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
        if _client_needs_name(client):
            await _reply(update, context, config.ask_name_message or "Por favor, escribe tu nombre completo.", reply_markup=ReplyKeyboardRemove())
            _set_conversation_step(context.user_data.get("conversation_id"), "ASK_NAME")
            return ASK_NAME
        if config.collect_phone and not client.phone:
            await _reply(update, context, config.ask_phone_message or "Escribe tu número de celular para confirmar la cita.", reply_markup=ReplyKeyboardRemove())
            _set_conversation_step(context.user_data.get("conversation_id"), "ASK_PHONE")
            return ASK_PHONE
        return await _continue_after_contact_details(update, context, db, tenant, config)
    finally:
        db.close()


async def confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip().upper()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        if text not in {"SI", "SÍ", "YES"}:
            await _reply(update, context, config.cancel_message or "Tu cita ha sido cancelada.", reply_markup=ReplyKeyboardRemove())
            _set_conversation_step(context.user_data.get("conversation_id"), "CANCELLED")
            return ConversationHandler.END
        return await _create_appointment(update, context, db, config)
    finally:
        db.close()


async def my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/citas")
        appointments = appointment_repository.get_active_appointments_for_client(
            db,
            tenant.id,
            client.id,
            limit=10,
        )
        if not appointments:
            await _reply(update, context, "No tienes citas activas en este momento.")
            return ConversationHandler.END
        lines = ["Tus próximas citas:"]
        for appointment in appointments:
            lines.append(_cancel_appointment_label(appointment))
        await _reply(update, context, "\n".join(lines))
        return ConversationHandler.END
    finally:
        db.close()


async def cancel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/cancelar")
        if not config.allow_cancellation:
            await _reply(
                update,
                context,
                _format_message(
                    _config_message(config, "cancellation_disabled_message", CANCELLATION_DISABLED_MESSAGE),
                    _variables(tenant, config, client),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        appointments = appointment_repository.get_active_appointments_for_client(
            db,
            tenant.id,
            client.id,
            limit=10,
        )
        if not appointments:
            await _reply(
                update,
                context,
                _format_message(
                    _config_message(config, "cancel_no_appointments_message", CANCEL_NO_APPOINTMENTS_MESSAGE),
                    _variables(tenant, config, client),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END

        start_message = _format_message(
            _config_message(config, "cancel_start_message", CANCEL_START_MESSAGE),
            _variables(tenant, config, client),
        )
        if len(appointments) == 1:
            appointment = appointments[0]
            service, values = _cancel_appointment_values(tenant, config, client, appointment)
            context.user_data["cancel_appointment_id"] = appointment.id
            context.user_data.pop("cancel_options", None)
            confirm_text = _format_message(
                "Tienes una cita para {service_name} el {date} a las {time}. ¿Deseas cancelarla?",
                values,
            )
            message = "\n\n".join(part for part in [start_message, confirm_text] if part)
            await _reply(update, context, message, reply_markup=_cancel_confirm_keyboard())
            _set_conversation_step(
                conversation.id,
                "CANCEL_CONFIRM_APPOINTMENT",
                {"appointment_id": appointment.id, "service_id": service.id if service else None},
            )
            return CANCEL_CONFIRM_APPOINTMENT

        labels, options = _build_cancel_options(appointments)
        context.user_data["cancel_options"] = options
        context.user_data.pop("cancel_appointment_id", None)
        select_message = _format_message(
            _config_message(config, "cancel_select_message", CANCEL_SELECT_MESSAGE),
            _variables(tenant, config, client),
        )
        message = "\n\n".join(part for part in [start_message, select_message] if part)
        await _reply(update, context, message, reply_markup=_keyboard(labels, columns=1))
        _set_conversation_step(conversation.id, "CANCEL_SELECT_APPOINTMENT", {"options": options})
        return CANCEL_SELECT_APPOINTMENT
    finally:
        db.close()


async def cancel_select_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    cancel_options = context.user_data.get("cancel_options", {})
    appointment_id = cancel_options.get(text)
    if not appointment_id:
        reply_markup = _keyboard(list(cancel_options.keys()), columns=1) if cancel_options else ReplyKeyboardRemove()
        await _reply(update, context, "Selecciona una cita de la lista.", reply_markup=reply_markup)
        return CANCEL_SELECT_APPOINTMENT

    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.id == appointment_id,
                Appointment.tenant_id == context.user_data["tenant_id"],
                Appointment.client_id == context.user_data["client_id"],
            )
            .first()
        )
        if not appointment or not appointment_repository.can_cancel_appointment(appointment):
            tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
            client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
            await _reply(
                update,
                context,
                _format_message(
                    _config_message(config, "cancel_no_appointments_message", CANCEL_NO_APPOINTMENTS_MESSAGE),
                    _variables(tenant, config, client),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        context.user_data["cancel_appointment_id"] = appointment.id
        values = _variables(
            db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first(),
            config,
            db.query(Client).filter(Client.id == context.user_data["client_id"]).first(),
            service,
            extra=_cancel_appointment_extra(appointment),
            appointment=appointment,
        )
        await _reply(
            update,
            context,
            _format_message(_config_message(config, "cancel_confirm_message", CANCEL_CONFIRM_MESSAGE), values),
            reply_markup=_cancel_confirm_keyboard(),
        )
        _set_conversation_step(
            context.user_data.get("conversation_id"),
            "CANCEL_CONFIRM_APPOINTMENT",
            {"appointment_id": appointment.id, "service_id": service.id if service else None},
        )
        return CANCEL_CONFIRM_APPOINTMENT
    finally:
        db.close()


async def cancel_confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    appointment_id = context.user_data.get("cancel_appointment_id")
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        tenant = db.query(Tenant).filter(Tenant.id == context.user_data["tenant_id"]).first()
        client = db.query(Client).filter(Client.id == context.user_data["client_id"]).first()
        if not _is_cancel_confirmation(text):
            if not _is_cancel_rejection(text):
                await _reply(update, context, "Responde Sí, cancelar cita o No, conservar cita.", reply_markup=_cancel_confirm_keyboard())
                return CANCEL_CONFIRM_APPOINTMENT
            await _reply(
                update,
                context,
                _format_message(
                    _config_message(config, "cancel_rejected_message", CANCEL_REJECTED_MESSAGE),
                    _variables(tenant, config, client),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            _set_conversation_step(context.user_data.get("conversation_id"), "CANCELLED")
            context.user_data.pop("cancel_appointment_id", None)
            context.user_data.pop("cancel_options", None)
            return ConversationHandler.END

        if not appointment_id:
            await _reply(update, context, "No encontré la cita a cancelar. Escribe /cancelar para intentarlo de nuevo.", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.id == appointment_id,
                Appointment.tenant_id == context.user_data["tenant_id"],
                Appointment.client_id == context.user_data["client_id"],
            )
            .first()
        )
        if not appointment or not appointment_repository.can_cancel_appointment(appointment):
            await _reply(
                update,
                context,
                _format_message(
                    _config_message(config, "cancel_no_appointments_message", CANCEL_NO_APPOINTMENTS_MESSAGE),
                    _variables(tenant, config, client),
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END

        appointment_repository.cancel_appointment(
            db,
            appointment.id,
            tenant_id=context.user_data["tenant_id"],
            client_id=context.user_data["client_id"],
            reason="Cancelada por cliente desde Telegram",
        )
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        values = _variables(tenant, config, client, service, extra=_cancel_appointment_extra(appointment), appointment=appointment)
        success_template = _config_message(
            config,
            "cancel_success_message",
            (config.cancel_message if config else None) or CANCEL_SUCCESS_MESSAGE,
        )
        await _reply(update, context, _format_message(success_template, values), reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(context.user_data.get("conversation_id"), "CANCELLED")
        context.user_data.pop("cancel_appointment_id", None)
        context.user_data.pop("cancel_options", None)
        return ConversationHandler.END
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/ayuda")
        command_config = _find_command(config, "/ayuda")
        if command_config and command_config.get("message"):
            message = _format_message(command_config["message"], _variables(tenant, config, client))
        else:
            active = [item for item in _command_configs(config) if item.get("is_active", True)]
            lines = ["Comandos disponibles:"]
            lines.extend(f"{item['command']} - {item['description']}" for item in active)
            message = "\n".join(lines)
        await _reply(update, context, message, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(conversation.id, "HELP_SHOWN")
        return ConversationHandler.END
    finally:
        db.close()


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/servicios")
        command_config = _find_command(config, "/servicios")
        return await _show_services_readonly(
            update,
            context,
            db,
            tenant,
            config,
            command_config.get("message") if command_config else None,
        )
    finally:
        db.close()


async def schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or "/horarios")
        command_config = _find_command(config, "/horarios")
        return await _show_available_schedule(
            update,
            context,
            db,
            tenant,
            config,
            command_config.get("message") if command_config else None,
        )
    finally:
        db.close()


async def dynamic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    command = _normalize_command_name(update.effective_message.text or "")
    try:
        _save_message(conversation.id, "incoming", update.effective_message.text or command)
        command_config = _find_command(config, command)
        if not command_config:
            await _reply(update, context, UNKNOWN_MESSAGE)
            _set_conversation_step(conversation.id, "UNKNOWN_COMMAND", {"command": command})
            return ConversationHandler.END

        action = command_config.get("action_type")
        message = command_config.get("message")
        if action == "iniciar_agendamiento":
            if message:
                await _reply(update, context, _format_message(message, _variables(tenant, config, client)))
            return await _show_services(update, context, db, tenant, config)
        if action == "mostrar_servicios":
            return await _show_services_readonly(update, context, db, tenant, config, message)
        if action == "mostrar_horarios":
            return await _show_available_schedule(update, context, db, tenant, config, message)
        if action == "mostrar_citas_cliente":
            db.close()
            return await my_appointments(update, context)
        if action == "cancelar_cita":
            db.close()
            return await cancel_start(update, context)
        if action == "mostrar_ayuda":
            if message:
                await _reply(update, context, _format_message(message, _variables(tenant, config, client)))
                _set_conversation_step(conversation.id, "HELP_SHOWN")
                return ConversationHandler.END
            db.close()
            return await help_command(update, context)

        response = _format_message(message, _variables(tenant, config, client)) if message else (
            "Recibí tu mensaje. Escribe /ayuda para ver lo que puedo hacer."
        )
        await _reply(update, context, response, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(conversation.id, "CUSTOM_COMMAND", {"command": command})
        return ConversationHandler.END
    finally:
        if db.is_active:
            db.close()


async def text_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    text = update.effective_message.text or ""
    try:
        _save_message(conversation.id, "incoming", text)
        if _is_greeting(text):
            await _reply(update, context, _format_message(GREETING_RESPONSE, _variables(tenant, config, client)))
            return await _show_services(update, context, db, tenant, config)

        await _reply(update, context, UNKNOWN_MESSAGE, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(conversation.id, "ORIENTATION")
        return ConversationHandler.END
    finally:
        db.close()


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, text_entry),
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_selected)],
            SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_selected)],
            CONFIRM_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_appointment)],
            CANCEL_SELECT_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_select_appointment)],
            CANCEL_CONFIRM_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_confirm_appointment)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("servicios", services_command),
            CommandHandler("horarios", schedules_command),
            CommandHandler("citas", my_appointments),
            CommandHandler("cancelar", cancel_start),
            CommandHandler("ayuda", help_command),
            MessageHandler(filters.COMMAND, dynamic_command),
        ],
    )


async def callback_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    boot = _bootstrap(update, context)
    if not boot:
        return ConversationHandler.END
    db, tenant, config, client, conversation = boot
    query = update.callback_query
    try:
        if query:
            await query.answer()
            _save_message(conversation.id, "incoming", f"callback:{query.data or ''}")
        await _reply(update, context, UNKNOWN_MESSAGE, reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(conversation.id, "UNKNOWN_CALLBACK", {"callback_data": query.data if query else None})
        return ConversationHandler.END
    finally:
        db.close()


async def telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tenant_id = context.application.bot_data.get("tenant_id")
    message = _safe_error_message(context.error or "Error desconocido")
    status = "conflict" if isinstance(context.error, Conflict) else "error"
    if tenant_id:
        _set_config_runtime_status(tenant_id, listener_status=status, last_bot_error=message)
    logger.error("[Telegram] Error procesando mensaje para tenant %s: %s", tenant_id, message)


def configure_application_handlers(application: Application) -> None:
    application.add_handler(build_conversation_handler())
    application.add_handler(CommandHandler("servicios", services_command))
    application.add_handler(CommandHandler("horarios", schedules_command))
    application.add_handler(CommandHandler("citas", my_appointments))
    application.add_handler(CommandHandler("cancelar", cancel_start))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CallbackQueryHandler(callback_entry))
    application.add_handler(MessageHandler(filters.COMMAND, dynamic_command))
    application.add_error_handler(telegram_error_handler)


@dataclass
class BotRuntime:
    tenant_id: int
    tenant_name: str
    bot_id: Optional[str]
    bot_username: Optional[str]
    token_fingerprint: str
    application: Application


class TelegramBotManager:
    def __init__(self, *, reload_interval_seconds: int = 30, console_output: bool = True):
        self.reload_interval_seconds = reload_interval_seconds
        self.console_output = console_output
        self.runtimes: dict[int, BotRuntime] = {}
        self._reload_lock = asyncio.Lock()
        self._reload_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._started = False
        self._empty_reported = False

    @property
    def active_count(self) -> int:
        return len(self.runtimes)

    @property
    def is_started(self) -> bool:
        return self._started

    def is_running_for_tenant(self, tenant_id: int) -> bool:
        return tenant_id in self.runtimes

    def _print(self, message: str) -> None:
        if self.console_output:
            print(message)

    def load_bots(self) -> list[dict[str, Any]]:
        db = SessionLocal()
        try:
            configs = (
                db.query(TelegramConfig)
                .options(joinedload(TelegramConfig.tenant))
                .join(Tenant, TelegramConfig.tenant_id == Tenant.id)
                .filter(
                    TelegramConfig.is_connected == True,
                    TelegramConfig.bot_token_encrypted.isnot(None),
                    Tenant.is_active == True,
                )
                .all()
            )
            bots = []
            for config in configs:
                try:
                    token = decrypt_token(config.bot_token_encrypted)
                except Exception as exc:
                    message = _safe_error_message(exc)
                    logger.error("[Telegram] No se pudo descifrar el token de tenant %s: %s", config.tenant_id, message)
                    config.listener_status = "error"
                    config.last_bot_error = "No se pudo descifrar el token protegido del bot."
                    db.commit()
                    continue
                if not token:
                    logger.error(
                        "[Telegram] No se pudo iniciar @%s para tenant %s porque su token no se pudo descifrar.",
                        config.bot_username or "sin_usuario",
                        config.tenant_id,
                    )
                    config.listener_status = "error"
                    config.last_bot_error = "No se pudo descifrar el token protegido del bot."
                    db.commit()
                    continue
                bots.append(
                    {
                        "tenant_id": config.tenant_id,
                        "tenant_name": config.tenant.name if config.tenant else f"Tenant {config.tenant_id}",
                        "bot_id": config.bot_id,
                        "bot_username": config.bot_username,
                        "token": token,
                        "token_fingerprint": _token_fingerprint(token),
                    }
                )
            return bots
        finally:
            db.close()

    async def start(self) -> None:
        if self._started:
            return
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._started = True
        self._print("Servicio Telegram: cargando bots conectados...")
        await self.reload()
        self._reload_task = asyncio.create_task(self._periodic_reload(), name="telegram-bot-reloader")

    async def stop(self) -> None:
        if not self._started and not self.runtimes:
            return
        self._started = False
        if self._stop_event:
            self._stop_event.set()
        if self._reload_task:
            self._reload_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reload_task
            self._reload_task = None
        for tenant_id in list(self.runtimes):
            await self.stop_bot_for_tenant(tenant_id)

    async def wait_until_stopped(self) -> None:
        if not self._stop_event:
            self._stop_event = asyncio.Event()
        await self._stop_event.wait()

    def request_reload(self) -> bool:
        if not self._started or not self._loop or self._loop.is_closed():
            return False
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self._loop:
            self._loop.create_task(self.reload())
        else:
            asyncio.run_coroutine_threadsafe(self.reload(), self._loop)
        return True

    async def reload(self) -> None:
        async with self._reload_lock:
            bots = self.load_bots()
            desired_by_tenant = {int(bot["tenant_id"]): bot for bot in bots}

            for tenant_id, runtime in list(self.runtimes.items()):
                desired = desired_by_tenant.get(tenant_id)
                if not desired or desired["token_fingerprint"] != runtime.token_fingerprint:
                    await self.stop_bot_for_tenant(tenant_id)

            if not desired_by_tenant:
                if not self._empty_reported:
                    self._print("Servicio Telegram: no hay bots conectados. Configura un bot desde el panel del negocio.")
                    self._empty_reported = True
                return

            self._empty_reported = False
            for bot in desired_by_tenant.values():
                try:
                    await self.start_bot_for_config(bot)
                except Exception as exc:
                    message = _safe_error_message(exc)
                    tenant_id = int(bot["tenant_id"])
                    _set_config_runtime_status(tenant_id, listener_status="error", last_bot_error=message)
                    logger.error("[Telegram] No se pudo iniciar @%s para tenant %s: %s", bot.get("bot_username") or "sin_usuario", tenant_id, message)

            self._print(f"Bots de Telegram activos: {self.active_count}")

    async def start_bot_for_config(self, bot: dict[str, Any]) -> None:
        tenant_id = int(bot["tenant_id"])
        runtime = self.runtimes.get(tenant_id)
        if runtime and runtime.token_fingerprint == bot["token_fingerprint"]:
            return
        if runtime:
            await self.stop_bot_for_tenant(tenant_id)

        username = bot.get("bot_username") or "sin_usuario"
        logger.info("[Telegram] Iniciando bot @%s para tenant %s", username, tenant_id)
        application = Application.builder().token(bot["token"]).build()
        application.bot_data.update(
            {
                "tenant_id": tenant_id,
                "tenant_name": bot["tenant_name"],
                "bot_id": bot["bot_id"],
            }
        )
        configure_application_handlers(application)

        try:
            await application.initialize()
            await application.bot.delete_webhook(drop_pending_updates=False)
            await application.start()
            if not application.updater:
                raise RuntimeError("La instancia de Telegram no tiene updater para polling.")
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        except Conflict:
            await self._stop_application(application)
            _set_config_runtime_status(tenant_id, listener_status="conflict", last_bot_error=CONFLICT_MESSAGE)
            logger.error("[Telegram] %s Tenant %s, bot @%s", CONFLICT_MESSAGE, tenant_id, username)
            self._print(CONFLICT_MESSAGE)
            return
        except InvalidToken:
            await self._stop_application(application)
            message = "Telegram rechazó el token guardado para este bot."
            _set_config_runtime_status(
                tenant_id,
                listener_status="error",
                last_bot_error=message,
                connection_status="token_invalid",
            )
            logger.error("[Telegram] %s Tenant %s, bot @%s", message, tenant_id, username)
            return
        except TelegramError as exc:
            await self._stop_application(application)
            message = _safe_error_message(exc)
            status = "conflict" if isinstance(exc, Conflict) else "error"
            if isinstance(exc, Conflict):
                message = CONFLICT_MESSAGE
            _set_config_runtime_status(tenant_id, listener_status=status, last_bot_error=message)
            logger.error("[Telegram] Error iniciando bot @%s para tenant %s: %s", username, tenant_id, message)
            return
        except Exception as exc:
            await self._stop_application(application)
            message = _safe_error_message(exc)
            _set_config_runtime_status(tenant_id, listener_status="error", last_bot_error=message)
            logger.error("[Telegram] Error iniciando bot @%s para tenant %s: %s", username, tenant_id, message)
            return

        self.runtimes[tenant_id] = BotRuntime(
            tenant_id=tenant_id,
            tenant_name=bot["tenant_name"],
            bot_id=bot.get("bot_id"),
            bot_username=bot.get("bot_username"),
            token_fingerprint=bot["token_fingerprint"],
            application=application,
        )
        _set_config_runtime_status(
            tenant_id,
            listener_status="active",
            listener_started_at=datetime.now(timezone.utc),
            clear_error=True,
            connection_status="connected",
        )
        logger.info("[Telegram] Bot @%s conectado para negocio %s", username, bot["tenant_name"])
        self._print(f"Bot conectado: @{username} para negocio {bot['tenant_name']}")

    async def stop_bot_for_tenant(self, tenant_id: int) -> None:
        runtime = self.runtimes.pop(int(tenant_id), None)
        if not runtime:
            return
        await self._stop_application(runtime.application)
        _set_config_runtime_status(int(tenant_id), listener_status="inactive")
        logger.info("[Telegram] Bot @%s detenido para tenant %s", runtime.bot_username or "sin_usuario", tenant_id)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, tenant_id: int) -> int:
        context.application.bot_data["tenant_id"] = tenant_id
        return await text_entry(update, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, tenant_id: int) -> int:
        context.application.bot_data["tenant_id"] = tenant_id
        return await callback_entry(update, context)

    async def _periodic_reload(self) -> None:
        while self._started:
            try:
                if self._stop_event:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.reload_interval_seconds)
                    return
                await asyncio.sleep(self.reload_interval_seconds)
                await self.reload()
            except asyncio.TimeoutError:
                await self.reload()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("[Telegram] Error recargando bots: %s", _safe_error_message(exc))

    async def _stop_application(self, application: Application) -> None:
        with contextlib.suppress(Exception):
            if application.updater and application.updater.running:
                await application.updater.stop()
        with contextlib.suppress(Exception):
            if application.running:
                await application.stop()
        with contextlib.suppress(Exception):
            await application.shutdown()

    async def run(self) -> None:
        create_tables()
        print("Iniciando bots de Telegram configurados...")
        try:
            await self.start()
            if self.active_count == 0:
                print("No hay bots de Telegram conectados. Configura un bot desde el panel de Turnix.")
            else:
                print(f"Bots activos: {self.active_count}")
            print("Escuchando mensajes de Telegram...")
            await self.wait_until_stopped()
        finally:
            await self.stop()


_telegram_bot_manager: Optional[TelegramBotManager] = None


def set_telegram_bot_manager(manager: Optional[TelegramBotManager]) -> None:
    global _telegram_bot_manager
    _telegram_bot_manager = manager


def get_telegram_bot_manager() -> Optional[TelegramBotManager]:
    return _telegram_bot_manager


def is_tenant_bot_running(tenant_id: int) -> bool:
    return bool(_telegram_bot_manager and _telegram_bot_manager.is_running_for_tenant(tenant_id))


def request_telegram_reload() -> bool:
    return bool(_telegram_bot_manager and _telegram_bot_manager.request_reload())


def main():
    try:
        manager = TelegramBotManager()
        set_telegram_bot_manager(manager)
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        pass
    finally:
        set_telegram_bot_manager(None)
        print("Bots de Telegram detenidos.")


if __name__ == "__main__":
    main()
