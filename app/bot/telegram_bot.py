"""Runtime multi-bot de Telegram para Turnix.

Uso:
  python -m app.bot.telegram_bot

Cada tenant conecta su propio bot desde el panel. Este runtime local usa polling
para iniciar una instancia de Telegram por cada configuración conectada.
"""
import asyncio
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import InvalidToken, TelegramError
from telegram.ext import (
    Application,
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
from app.services.plan_usage_service import INTERNAL_LIMIT_MESSAGE, can_create_appointment
from app.services.telegram_token_service import decrypt_token

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

ASK_NAME, ASK_PHONE, SELECT_SERVICE, SELECT_DATE, SELECT_TIME, CONFIRM_APPOINTMENT, CANCEL_APPOINTMENT = range(7)

NO_SERVICES_MESSAGE = "Este negocio aún no tiene servicios disponibles para agendar."
DEFAULT_COMMANDS: list[dict[str, Any]] = [
    {
        "command": "/start",
        "description": "Iniciar reservas",
        "action_type": "iniciar_agendamiento",
        "message": "Hola. Bienvenido a {business_name}. Vamos a agendar tu cita.",
        "is_active": True,
    },
    {
        "command": "/servicios",
        "description": "Ver servicios",
        "action_type": "mostrar_servicios",
        "message": "Estos son nuestros servicios disponibles:",
        "is_active": True,
    },
    {
        "command": "/horarios",
        "description": "Ver horarios disponibles",
        "action_type": "mostrar_horarios",
        "message": "Estos son los próximos horarios disponibles:",
        "is_active": True,
    },
    {
        "command": "/citas",
        "description": "Ver mis citas",
        "action_type": "mostrar_citas_cliente",
        "message": None,
        "is_active": True,
    },
    {
        "command": "/cancelar",
        "description": "Cancelar una cita",
        "action_type": "cancelar_cita",
        "message": "Vamos a revisar tus citas activas para cancelar la que elijas.",
        "is_active": True,
    },
    {
        "command": "/ayuda",
        "description": "Obtener ayuda",
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


class SafeDict(defaultdict):
    def __missing__(self, key):
        return "{" + key + "}"


def _format_message(template: Optional[str], values: dict[str, Any]) -> str:
    try:
        return (template or "").format_map(SafeDict(str, {k: "" if v is None else v for k, v in values.items()}))
    except Exception:
        return template or ""


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


def _variables(tenant: Tenant, config: TelegramConfig, client: Optional[Client] = None, service: Optional[Service] = None, extra=None):
    extra = extra or {}
    return {
        "business_name": tenant.name if tenant else "",
        "service_name": service.name if service else extra.get("service_name", ""),
        "date": extra.get("date", ""),
        "time": extra.get("time", ""),
        "client_name": client.full_name if client else extra.get("client_name", ""),
        "phone": client.phone if client else extra.get("phone", ""),
        "price": f"${int(service.price):,}" if service else extra.get("price", ""),
        "duration": f"{service.duration_minutes} min" if service else extra.get("duration", ""),
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
    await update.effective_message.reply_text(text, **kwargs)
    _save_message(context.user_data.get("conversation_id"), "outgoing", text)


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
        lines = [_format_message(config.ask_date_message or "Cuando quieres agendar tu cita?", _variables(tenant, config, service=service))]
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
        {"date": context.user_data["selected_date"], "time": selected_time},
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
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.tenant_id == tenant.id,
                Appointment.client_id == client.id,
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )
        if not appointments:
            await _reply(update, context, "No tienes citas activas en este momento.")
            return ConversationHandler.END
        lines = ["Tus próximas citas:"]
        for appointment in appointments:
            service = db.query(Service).filter(Service.id == appointment.service_id).first()
            lines.append(f"#{appointment.id} - {service.name if service else 'Servicio'} - {appointment.appointment_date} {appointment.start_time.strftime('%H:%M')}")
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
            await _reply(update, context, "La cancelación por Telegram no está habilitada para este negocio.")
            return ConversationHandler.END
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.tenant_id == tenant.id,
                Appointment.client_id == client.id,
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )
        if not appointments:
            await _reply(update, context, "No tienes citas activas para cancelar.")
            return ConversationHandler.END
        lines = ["Escribe el ID de la cita que deseas cancelar:"]
        for appointment in appointments:
            service = db.query(Service).filter(Service.id == appointment.service_id).first()
            lines.append(f"#{appointment.id} - {service.name if service else 'Servicio'} - {appointment.appointment_date} {appointment.start_time.strftime('%H:%M')}")
        await _reply(update, context, "\n".join(lines), reply_markup=ReplyKeyboardRemove())
        _set_conversation_step(conversation.id, "CANCEL_APPOINTMENT")
        return CANCEL_APPOINTMENT
    finally:
        db.close()


async def cancel_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    try:
        appointment_id = int(text.replace("#", ""))
    except ValueError:
        await _reply(update, context, "Escribe un ID numérico válido.")
        return CANCEL_APPOINTMENT

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
        if not appointment:
            await _reply(update, context, "No se encontró la cita o no pertenece a esta conversación.")
            return CANCEL_APPOINTMENT
        appointment.status = "cancelled"
        db.commit()
        await _reply(update, context, config.cancel_message or "Tu cita ha sido cancelada.")
        _set_conversation_step(context.user_data.get("conversation_id"), "CANCELLED")
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
            await _reply(update, context, "No reconozco ese comando. Escribe /ayuda para ver las opciones disponibles.")
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
        if bool(config.auto_start_on_greeting) and _is_greeting(text):
            welcome = _format_message(config.welcome_message, _variables(tenant, config, client))
            await _reply(update, context, welcome or f"Hola. Bienvenido a {tenant.name}.")
            return await _show_services(update, context, db, tenant, config)

        message = (
            f"Hola. Bienvenido a {tenant.name}. "
            "Puedes usar /start para agendar una cita, /servicios para ver nuestros servicios "
            "o /ayuda para revisar las opciones disponibles."
        )
        await _reply(update, context, message, reply_markup=ReplyKeyboardRemove())
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
            CANCEL_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_by_id)],
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


class BotManager:
    def __init__(self):
        self.apps: list[Application] = []
        self.started_keys: set[str] = set()

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
                token = decrypt_token(config.bot_token_encrypted)
                if not token:
                    logger.error("No se pudo iniciar @%s porque su token no se pudo descifrar.", config.bot_username or "sin_usuario")
                    continue
                bots.append(
                    {
                        "tenant_id": config.tenant_id,
                        "tenant_name": config.tenant.name,
                        "bot_id": config.bot_id,
                        "bot_username": config.bot_username,
                        "token": token,
                    }
                )
            return bots
        finally:
            db.close()

    async def start_bot(self, bot: dict[str, Any]) -> None:
        bot_key = str(bot["tenant_id"])
        if bot_key in self.started_keys:
            return
        application = Application.builder().token(bot["token"]).build()
        application.bot_data.update(
            {
                "tenant_id": bot["tenant_id"],
                "tenant_name": bot["tenant_name"],
                "bot_id": bot["bot_id"],
            }
        )
        application.add_handler(build_conversation_handler())
        application.add_handler(CommandHandler("servicios", services_command))
        application.add_handler(CommandHandler("horarios", schedules_command))
        application.add_handler(CommandHandler("citas", my_appointments))
        application.add_handler(CommandHandler("cancelar", cancel_start))
        application.add_handler(CommandHandler("ayuda", help_command))
        application.add_handler(MessageHandler(filters.COMMAND, dynamic_command))
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        self.apps.append(application)
        self.started_keys.add(bot_key)
        logger.info("Bot conectado: @%s para negocio %s", bot["bot_username"], bot["tenant_name"])

    async def run(self) -> None:
        create_tables()
        print("Iniciando bots de Telegram configurados...")
        try:
            warned_empty = False
            while True:
                bots = self.load_bots()
                if not bots and not warned_empty:
                    print("No hay bots de Telegram conectados. Configura un token desde el panel de Turnix.")
                    warned_empty = True
                for bot in bots:
                    try:
                        await self.start_bot(bot)
                    except InvalidToken:
                        logger.error("Telegram rechazó el token guardado para @%s.", bot.get("bot_username") or "sin_usuario")
                    except TelegramError as exc:
                        logger.error("No se pudo iniciar @%s: %s", bot.get("bot_username") or "sin_usuario", type(exc).__name__)
                await asyncio.sleep(30)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        for application in self.apps:
            if application.updater:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()


def main():
    try:
        asyncio.run(BotManager().run())
    except KeyboardInterrupt:
        print("Bots de Telegram detenidos.")


if __name__ == "__main__":
    main()
