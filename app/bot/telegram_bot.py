"""
Bot global de Telegram para Turnix.

Uso:
  python -m app.bot.telegram_bot

Flujo:
  /start <slug-negocio> -> menú -> servicios / agendar / mis citas / cancelar
"""
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import InvalidToken
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.core.config import settings
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
from app.services.availability_service import get_available_slots

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

MENU, SELECTING_SERVICE, ENTERING_DATE, SELECTING_SLOT, CONFIRMING_APPOINTMENT, CANCELLING_APPOINTMENT = range(6)

MISSING_SLUG_MESSAGE = (
    "Para iniciar, abre el enlace de Telegram generado desde el panel de Turnix "
    "para el negocio correspondiente."
)
BUSINESS_NOT_FOUND_MESSAGE = "No se encontró el negocio asociado a este enlace."
NO_SERVICES_MESSAGE = "Este negocio aún no tiene servicios disponibles para agendar."
MISSING_TOKEN_MESSAGE = "No se encontró TELEGRAM_BOT_TOKEN en el archivo .env."


def _get_tenant_by_slug(db, slug: str) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.slug == slug, Tenant.is_active == True).first()


def _get_config(db, tenant_id: int) -> TelegramConfig:
    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant_id).first()
    if config:
        return config
    config = TelegramConfig(tenant_id=tenant_id, use_global_bot=True)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _get_active_services(db, tenant_id: int):
    return (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.is_active == True)
        .order_by(Service.name)
        .all()
    )


def _get_or_create_client(db, tg_user, tenant_id: int) -> Client:
    full_name = (tg_user.full_name or "").strip() or "Cliente Telegram"
    client = (
        db.query(Client)
        .filter(Client.telegram_user_id == str(tg_user.id), Client.tenant_id == tenant_id)
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
        client.full_name = full_name
        client.username = tg_user.username
    db.commit()
    db.refresh(client)
    return client


def _get_or_create_conversation(db, client: Client, chat_id: int, tenant_id: int) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == tenant_id,
            Conversation.client_id == client.id,
            Conversation.chat_id == str(chat_id),
        )
        .first()
    )
    if not conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            client_id=client.id,
            chat_id=str(chat_id),
            channel="telegram",
            status="active",
            visit_count=1,
        )
        db.add(conversation)
    else:
        conversation.visit_count = (conversation.visit_count or 0) + 1
        conversation.last_interaction_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
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


def _menu_keyboard(config: TelegramConfig) -> ReplyKeyboardMarkup:
    rows = [["Ver servicios", "Agendar cita"], ["Mis citas"]]
    if config.allow_cancellation:
        rows[-1].append("Cancelar cita")
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _service_line(service: Service, config: TelegramConfig, index: Optional[int] = None) -> str:
    prefix = f"{index}. " if index is not None else "- "
    parts = [f"{prefix}{service.name}"]
    if config.show_duration:
        parts.append(f"{service.duration_minutes} min")
    if config.show_prices:
        parts.append(f"${int(service.price):,}")
    line = " - ".join(parts)
    if service.description:
        line += f"\n  {service.description}"
    return line


def _services_prompt(services, config: TelegramConfig) -> str:
    lines = [config.services_message or "Estos son nuestros servicios disponibles:"]
    lines.extend(_service_line(service, config, i + 1) for i, service in enumerate(services))
    lines.append("Escribe el número del servicio para agendar.")
    return "\n".join(lines)


async def _reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs) -> None:
    await update.message.reply_text(text, **kwargs)
    _save_message(context.user_data.get("conversation_id"), "outgoing", text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    slug = context.args[0].strip().lower() if context.args else None
    db = SessionLocal()
    try:
        if not slug:
            await update.message.reply_text(MISSING_SLUG_MESSAGE)
            return ConversationHandler.END

        tenant = _get_tenant_by_slug(db, slug)
        if not tenant:
            await update.message.reply_text(BUSINESS_NOT_FOUND_MESSAGE)
            return ConversationHandler.END

        config = _get_config(db, tenant.id)
        services = _get_active_services(db, tenant.id)
        client = _get_or_create_client(db, update.effective_user, tenant.id)
        conversation = _get_or_create_conversation(db, client, update.effective_chat.id, tenant.id)

        context.user_data.clear()
        context.user_data.update(
            {
                "tenant_id": tenant.id,
                "tenant_slug": tenant.slug,
                "client_id": client.id,
                "conversation_id": conversation.id,
            }
        )

        incoming = f"/start {slug}"
        _save_message(conversation.id, "incoming", incoming)

        welcome = config.welcome_message or f"Bienvenido a {tenant.name}. ¿En qué puedo ayudarte?"
        if "{business}" in welcome:
            welcome = welcome.replace("{business}", tenant.name)

        if not services:
            await _reply(
                update,
                context,
                f"{welcome}\n\n{NO_SERVICES_MESSAGE}",
                reply_markup=ReplyKeyboardRemove(),
            )
            return MENU

        context.user_data["services_list"] = {str(i + 1): service.id for i, service in enumerate(services)}
        await _reply(
            update,
            context,
            f"{welcome}\n\n{_services_prompt(services, config)}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return SELECTING_SERVICE
    finally:
        db.close()


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    if not context.user_data.get("tenant_id"):
        await update.message.reply_text(MISSING_SLUG_MESSAGE)
        return ConversationHandler.END

    normalized = text.lower()

    if "servicio" in normalized:
        return await show_services(update, context)
    if "agendar" in normalized or "cita" == normalized:
        return await start_booking(update, context)
    if "mis citas" in normalized:
        return await show_my_appointments(update, context)
    if "cancelar" in normalized:
        return await start_cancellation(update, context)

    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        await _reply(update, context, "Elige una opción del menú.", reply_markup=_menu_keyboard(config))
    finally:
        db.close()
    return MENU


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        services = _get_active_services(db, context.user_data["tenant_id"])
        if not services:
            await _reply(update, context, NO_SERVICES_MESSAGE)
            return MENU

        lines = [config.services_message or "Estos son nuestros servicios disponibles:"]
        lines.extend(_service_line(service, config) for service in services)
        await _reply(update, context, "\n".join(lines))
    finally:
        db.close()
    return MENU


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        services = _get_active_services(db, context.user_data["tenant_id"])
        if not services:
            await _reply(update, context, NO_SERVICES_MESSAGE)
            return MENU

        context.user_data["services_list"] = {str(i + 1): service.id for i, service in enumerate(services)}
        await _reply(update, context, _services_prompt(services, config), reply_markup=ReplyKeyboardRemove())
    finally:
        db.close()
    return SELECTING_SERVICE


async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    if not context.user_data.get("tenant_id"):
        await update.message.reply_text(MISSING_SLUG_MESSAGE)
        return ConversationHandler.END

    service_id = context.user_data.get("services_list", {}).get(text)
    if not service_id:
        await _reply(update, context, "Escribe el número del servicio de la lista.")
        return SELECTING_SERVICE

    db = SessionLocal()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        config = _get_config(db, context.user_data["tenant_id"])
        context.user_data.update(
            {
                "selected_service_id": service.id,
                "selected_service_name": service.name,
                "selected_service_duration": service.duration_minutes,
                "selected_service_price": int(service.price),
            }
        )
        msg = (
            f"Seleccionaste: {service.name}\n\n"
            f"{config.ask_date_message or '¿Para qué fecha quieres la cita? (YYYY-MM-DD)'}"
        )
        await _reply(update, context, msg)
    finally:
        db.close()
    return ENTERING_DATE


async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    try:
        target_date = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await _reply(update, context, "Formato de fecha inválido. Usa YYYY-MM-DD.")
        return ENTERING_DATE

    if target_date < date.today():
        await _reply(update, context, "La fecha no puede ser en el pasado. Elige otra fecha.")
        return ENTERING_DATE

    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        slots = get_available_slots(
            db,
            context.user_data["tenant_id"],
            context.user_data["selected_service_id"],
            target_date,
        )
        if not slots:
            await _reply(update, context, config.unavailable_message or "No hay horarios disponibles para esa fecha.")
            return ENTERING_DATE

        context.user_data["selected_date"] = target_date
        context.user_data["slots_map"] = {str(i + 1): slot for i, slot in enumerate(slots)}
        lines = [config.ask_time_message or "Selecciona el horario disponible:"]
        lines.extend(f"{i + 1}. {slot}" for i, slot in enumerate(slots))
        lines.append("Escribe el número del horario.")
        await _reply(update, context, "\n".join(lines))
    finally:
        db.close()
    return SELECTING_SLOT


async def slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    selected_time = context.user_data.get("slots_map", {}).get(text)
    if not selected_time:
        await _reply(update, context, "Escribe el número del horario de la lista.")
        return SELECTING_SLOT

    context.user_data["selected_time"] = selected_time
    duration = context.user_data["selected_service_duration"]
    end_time = (datetime.strptime(selected_time, "%H:%M") + timedelta(minutes=duration)).strftime("%H:%M")
    summary = (
        "Resumen de tu cita:\n"
        f"Servicio: {context.user_data['selected_service_name']}\n"
        f"Fecha: {context.user_data['selected_date']}\n"
        f"Hora: {selected_time} - {end_time}\n"
        "Responde SI para confirmar o NO para cancelar."
    )
    await _reply(update, context, summary, reply_markup=ReplyKeyboardMarkup([["SI", "NO"]], resize_keyboard=True))
    return CONFIRMING_APPOINTMENT


async def confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().upper()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        keyboard = _menu_keyboard(config)
        if text != "SI":
            cancel_msg = config.cancel_message or "Tu cita ha sido cancelada."
            await _reply(update, context, f"{cancel_msg} ¿En qué más puedo ayudarte?", reply_markup=keyboard)
            return MENU

        appointment, error = appointment_repository.create_appointment(
            db,
            AppointmentCreate(
                tenant_id=context.user_data["tenant_id"],
                service_id=context.user_data["selected_service_id"],
                client_id=context.user_data["client_id"],
                appointment_date=context.user_data["selected_date"],
                start_time=datetime.strptime(context.user_data["selected_time"], "%H:%M").time(),
            ),
        )
        if error:
            await _reply(update, context, f"{error}\n¿En qué más puedo ayudarte?", reply_markup=keyboard)
            return MENU

        appointment.status = "confirmed"
        appointment.notes = "Cita creada desde Telegram"
        db.commit()
        db.refresh(appointment)

        msg = config.confirm_message or "Tu cita ha sido confirmada. Te esperamos."
        msg = (
            f"{msg}\n\n"
            f"Servicio: {context.user_data['selected_service_name']}\n"
            f"Fecha: {context.user_data['selected_date']}\n"
            f"Hora: {context.user_data['selected_time']}\n"
            f"Cita #{appointment.id}"
        )
        await _reply(update, context, msg, reply_markup=keyboard)
    finally:
        db.close()
    return MENU


async def show_my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.tenant_id == context.user_data["tenant_id"],
                Appointment.client_id == context.user_data["client_id"],
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )
        if not appointments:
            await _reply(update, context, "No tienes citas activas en este momento.")
            return MENU

        lines = ["Tus próximas citas:"]
        for appointment in appointments:
            service = db.query(Service).filter(Service.id == appointment.service_id).first()
            lines.append(
                f"#{appointment.id} - {service.name if service else 'Servicio'} - "
                f"{appointment.appointment_date} {appointment.start_time.strftime('%H:%M')} - {appointment.status}"
            )
        await _reply(update, context, "\n".join(lines))
    finally:
        db.close()
    return MENU


async def start_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        if not config.allow_cancellation:
            await _reply(update, context, "La cancelación por Telegram no está habilitada para este negocio.")
            return MENU

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.tenant_id == context.user_data["tenant_id"],
                Appointment.client_id == context.user_data["client_id"],
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )
        if not appointments:
            await _reply(update, context, "No tienes citas activas para cancelar.")
            return MENU

        lines = ["Escribe el ID de la cita que deseas cancelar:"]
        for appointment in appointments:
            service = db.query(Service).filter(Service.id == appointment.service_id).first()
            lines.append(
                f"#{appointment.id} - {service.name if service else 'Servicio'} - "
                f"{appointment.appointment_date} {appointment.start_time.strftime('%H:%M')}"
            )
        await _reply(update, context, "\n".join(lines), reply_markup=ReplyKeyboardRemove())
    finally:
        db.close()
    return CANCELLING_APPOINTMENT


async def cancel_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _save_message(context.user_data.get("conversation_id"), "incoming", text)
    try:
        appointment_id = int(text.replace("#", "").strip())
    except ValueError:
        await _reply(update, context, "Escribe un ID numérico válido.")
        return CANCELLING_APPOINTMENT

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
            msg = f"No encontré la cita #{appointment_id} o no pertenece a tu conversación."
        elif appointment.status in ("cancelled", "completed"):
            msg = f"La cita #{appointment_id} ya está {appointment.status}."
        else:
            appointment.status = "cancelled"
            db.commit()
            msg = config.cancel_message or f"La cita #{appointment_id} ha sido cancelada."
        await _reply(update, context, msg, reply_markup=_menu_keyboard(config))
    finally:
        db.close()
    return MENU


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _save_message(context.user_data.get("conversation_id"), "incoming", update.message.text or "")
    if not context.user_data.get("tenant_id"):
        await update.message.reply_text(MISSING_SLUG_MESSAGE)
        return ConversationHandler.END

    db = SessionLocal()
    try:
        config = _get_config(db, context.user_data["tenant_id"])
        await _reply(update, context, "No entendí eso. Usa una opción del menú.", reply_markup=_menu_keyboard(config))
    finally:
        db.close()
    return MENU


def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or token.strip().lower() in {"your_telegram_bot_token_here", "tu_token_de_telegram"}:
        logger.error(MISSING_TOKEN_MESSAGE)
        sys.exit(1)

    create_tables()
    application = Application.builder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            SELECTING_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_selected)],
            ENTERING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            SELECTING_SLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, slot_selected)],
            CONFIRMING_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_appointment)],
            CANCELLING_APPOINTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_by_id)],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message),
        ],
    )
    application.add_handler(conv_handler)
    logger.info("Bot global de Turnix iniciado. Esperando mensajes.")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except InvalidToken:
        logger.error("Telegram rechazó el token configurado. Verifica TELEGRAM_BOT_TOKEN en .env.")
        sys.exit(1)
    except Exception as exc:
        logger.error("El bot se detuvo por un error: %s", type(exc).__name__)
        sys.exit(1)


if __name__ == "__main__":
    main()
