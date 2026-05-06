"""
Bot de Telegram para Turnix – Sistema de Gestión de Citas de Belleza.

Flujo conversacional:
  /start → registro de cliente → menú principal
  1. Ver servicios
  2. Agendar cita
  3. Mis citas
  4. Cancelar cita

Uso:
  python -m app.bot.telegram_bot
"""
import logging
import os
import sys
from datetime import datetime, date, time, timedelta
from typing import Optional

# Ajustar path para poder importar la app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from app.core.config import settings
from app.core.database import SessionLocal, create_tables
from app.models.client import Client
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.appointment import Appointment
from app.repositories import appointment_repository
from app.schemas.appointment import AppointmentCreate
from app.services.availability_service import get_available_slots

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Estados del ConversationHandler
# ──────────────────────────────────────────────
(
    MENU,
    SELECTING_SERVICE,
    ENTERING_DATE,
    SELECTING_SLOT,
    CONFIRMING_APPOINTMENT,
    VIEWING_APPOINTMENTS,
    CANCELLING_APPOINTMENT,
) = range(7)

# ──────────────────────────────────────────────
# Helpers de base de datos
# ──────────────────────────────────────────────

def _get_or_create_client(db, tg_user) -> Client:
    """Registra o actualiza el cliente con datos de Telegram (sin aislamiento por tenant)."""
    client = db.query(Client).filter(Client.telegram_user_id == str(tg_user.id)).first()
    full_name = (tg_user.full_name or "").strip() or "Sin nombre"
    if not client:
        client = Client(
            telegram_user_id=str(tg_user.id),
            full_name=full_name,
            username=tg_user.username,
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    else:
        client.full_name = full_name
        client.username = tg_user.username
        db.commit()
    return client


def _get_or_create_client_for_tenant(db, tg_user, tenant_id: int) -> Client:
    """
    Registra o actualiza el cliente asociado a un tenant específico.
    Si el usuario ya existe para otro tenant, crea un registro separado por tenant.
    """
    full_name = (tg_user.full_name or "").strip() or "Sin nombre"
    client = (
        db.query(Client)
        .filter(
            Client.telegram_user_id == str(tg_user.id),
            Client.tenant_id == tenant_id,
        )
        .first()
    )
    if not client:
        client = Client(
            telegram_user_id=str(tg_user.id),
            full_name=full_name,
            username=tg_user.username,
            tenant_id=tenant_id,
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    else:
        client.full_name = full_name
        client.username  = tg_user.username
        db.commit()
    return client


def _get_or_create_conversation(db, client: Client, chat_id: int, tenant: Tenant) -> Conversation:
    """Crea o actualiza la conversación del cliente."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.client_id == client.id, Conversation.chat_id == str(chat_id))
        .first()
    )
    if not conv:
        conv = Conversation(
            tenant_id=tenant.id,
            client_id=client.id,
            chat_id=str(chat_id),
            channel="telegram",
            status="active",
            visit_count=1,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        conv.visit_count = (conv.visit_count or 0) + 1
        conv.last_interaction_at = datetime.utcnow()
        db.commit()
    return conv


def _save_message(conversation_id: int, direction: str, content: str):
    """Guarda un mensaje de conversación gestionando su propia sesión de base de datos."""
    db = SessionLocal()
    try:
        msg = Message(conversation_id=conversation_id, direction=direction, content=content)
        db.add(msg)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _get_default_tenant(db) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.is_active == True).first()


def _get_tenant_by_slug(db, slug: str) -> Optional[Tenant]:
    """Busca un tenant activo por su slug único."""
    return db.query(Tenant).filter(Tenant.slug == slug, Tenant.is_active == True).first()


def _resolve_tenant(db, context) -> Optional[Tenant]:
    """
    Determina qué tenant corresponde a la sesión.
    Prioridad:
      1. Si el usuario inició con /start <slug>, usar ese slug.
      2. Usar el slug guardado en user_data (sesión activa).
      3. Si solo hay un tenant activo, usarlo por defecto.
    """
    slug = (context.user_data or {}).get("tenant_slug")
    if slug:
        tenant = _get_tenant_by_slug(db, slug)
        if tenant:
            return tenant
    return _get_default_tenant(db)


def _get_active_services(db, tenant_id: int):
    return db.query(Service).filter(
        Service.tenant_id == tenant_id, Service.is_active == True
    ).all()


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        tg_user = update.effective_user

        # Identificar tenant por slug si se pasó como argumento: /start <slug>
        if context.args:
            slug = context.args[0].strip()
            context.user_data["tenant_slug"] = slug

        tenant = _resolve_tenant(db, context)
        if not tenant:
            await update.message.reply_text(
                "⚠️ El sistema aún no tiene un negocio configurado. "
                "Contacta al administrador."
            )
            return ConversationHandler.END

        # Asegurar que el cliente está asociado al tenant correcto
        client = _get_or_create_client_for_tenant(db, tg_user, tenant.id)
        conv = _get_or_create_conversation(db, client, update.effective_chat.id, tenant)

        _save_message(conv.id, "incoming", "/start")

        greeting = (
            f"👋 ¡Hola, {client.full_name}! Bienvenido/a a *{tenant.name}*.\n\n"
            "¿En qué puedo ayudarte hoy?"
        )

        keyboard = [
            ["1️⃣ Ver servicios", "2️⃣ Agendar cita"],
            ["3️⃣ Mis citas", "4️⃣ Cancelar cita"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(greeting, parse_mode="Markdown", reply_markup=reply_markup)
        _save_message(conv.id, "outgoing", greeting)

        context.user_data["tenant_id"] = tenant.id
        context.user_data["client_id"] = client.id
        context.user_data["conversation_id"] = conv.id

    finally:
        db.close()

    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    if "1" in text or "servicios" in text.lower():
        return await show_services(update, context)
    elif "2" in text or "agendar" in text.lower():
        return await start_booking(update, context)
    elif "3" in text or "mis citas" in text.lower():
        return await show_my_appointments(update, context)
    elif "4" in text or "cancelar" in text.lower():
        return await start_cancellation(update, context)
    else:
        await update.message.reply_text(
            "Por favor elige una opción del menú. 👆"
        )
        return MENU


# ── Ver servicios ──────────────────────────────

async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        tenant_id = context.user_data.get("tenant_id")
        services = _get_active_services(db, tenant_id)
        if not services:
            await update.message.reply_text("No hay servicios disponibles en este momento.")
            return MENU

        lines = ["*📋 Servicios disponibles:*\n"]
        for s in services:
            lines.append(
                f"• *{s.name}* – {s.duration_minutes} min – ${int(s.price):,}"
                + (f"\n  _{s.description}_" if s.description else "")
            )
        msg = "\n".join(lines)
        await update.message.reply_text(msg, parse_mode="Markdown")

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)
    finally:
        db.close()

    return MENU


# ── Agendar cita ──────────────────────────────

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        tenant_id = context.user_data.get("tenant_id")
        services = _get_active_services(db, tenant_id)
        if not services:
            await update.message.reply_text("No hay servicios disponibles para agendar.")
            return MENU

        context.user_data["services_list"] = {str(i + 1): s.id for i, s in enumerate(services)}

        lines = ["*¿Qué servicio deseas agendar?*\n"]
        for i, s in enumerate(services):
            lines.append(f"{i + 1}. {s.name} – {s.duration_minutes} min – ${int(s.price):,}")
        lines.append("\nEscribe el *número* del servicio.")
        msg = "\n".join(lines)

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)
    finally:
        db.close()

    return SELECTING_SERVICE


async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    services_map = context.user_data.get("services_list", {})

    if text not in services_map:
        await update.message.reply_text("Por favor escribe el número del servicio de la lista.")
        return SELECTING_SERVICE

    service_id = services_map[text]
    context.user_data["selected_service_id"] = service_id

    db = SessionLocal()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        context.user_data["selected_service_name"] = service.name
        context.user_data["selected_service_duration"] = service.duration_minutes
        context.user_data["selected_service_price"] = int(service.price)
    finally:
        db.close()

    msg = (
        f"Seleccionaste: *{context.user_data['selected_service_name']}*\n\n"
        "📅 ¿Para qué fecha quieres la cita?\n"
        "Escribe la fecha en formato *AAAA-MM-DD*\n"
        "_(ejemplo: 2026-05-10)_"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

    conv_id = context.user_data.get("conversation_id")
    if conv_id:
        _save_message(conv_id, "outgoing", msg)

    return ENTERING_DATE


async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        target_date = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(
            "Formato de fecha inválido. Escribe la fecha como *AAAA-MM-DD*\n_(ejemplo: 2026-05-10)_",
            parse_mode="Markdown",
        )
        return ENTERING_DATE

    if target_date < date.today():
        await update.message.reply_text("La fecha no puede ser en el pasado. Elige otra fecha.")
        return ENTERING_DATE

    context.user_data["selected_date"] = target_date

    db = SessionLocal()
    try:
        slots = get_available_slots(
            db,
            context.user_data["tenant_id"],
            context.user_data["selected_service_id"],
            target_date,
        )
    finally:
        db.close()

    if not slots:
        await update.message.reply_text(
            f"No hay horarios disponibles para el {text}. Prueba con otra fecha."
        )
        return ENTERING_DATE

    context.user_data["available_slots"] = slots
    context.user_data["slots_map"] = {str(i + 1): s for i, s in enumerate(slots)}

    lines = [f"*🕐 Horarios disponibles para el {text}:*\n"]
    for i, slot in enumerate(slots):
        lines.append(f"{i + 1}. {slot}")
    lines.append("\nEscribe el *número* del horario.")
    msg = "\n".join(lines)

    await update.message.reply_text(msg, parse_mode="Markdown")

    conv_id = context.user_data.get("conversation_id")
    if conv_id:
        _save_message(conv_id, "outgoing", msg)

    return SELECTING_SLOT


async def slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    slots_map = context.user_data.get("slots_map", {})

    if text not in slots_map:
        await update.message.reply_text("Por favor escribe el número del horario de la lista.")
        return SELECTING_SLOT

    selected_time_str = slots_map[text]
    context.user_data["selected_time"] = selected_time_str

    target_date = context.user_data["selected_date"]
    service_name = context.user_data["selected_service_name"]
    duration = context.user_data["selected_service_duration"]
    price = context.user_data["selected_service_price"]

    start_dt = datetime.strptime(selected_time_str, "%H:%M")
    end_dt = start_dt + timedelta(minutes=duration)

    summary = (
        "*✅ Resumen de tu cita:*\n\n"
        f"📌 Servicio: {service_name}\n"
        f"📅 Fecha: {target_date}\n"
        f"🕐 Hora: {selected_time_str} – {end_dt.strftime('%H:%M')}\n"
        f"💰 Precio: ${price:,}\n\n"
        "¿Confirmas la cita? Escribe *SI* para confirmar o *NO* para cancelar."
    )

    keyboard = [["SI", "NO"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=reply_markup)

    conv_id = context.user_data.get("conversation_id")
    if conv_id:
        _save_message(conv_id, "outgoing", summary)

    return CONFIRMING_APPOINTMENT


async def confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().upper()

    keyboard = [
        ["1️⃣ Ver servicios", "2️⃣ Agendar cita"],
        ["3️⃣ Mis citas", "4️⃣ Cancelar cita"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    if text != "SI":
        await update.message.reply_text(
            "Cita cancelada. ¿En qué más puedo ayudarte?",
            reply_markup=reply_markup,
        )
        return MENU

    db = SessionLocal()
    try:
        time_obj = datetime.strptime(context.user_data["selected_time"], "%H:%M").time()
        appt_create = AppointmentCreate(
            tenant_id=context.user_data["tenant_id"],
            service_id=context.user_data["selected_service_id"],
            client_id=context.user_data["client_id"],
            appointment_date=context.user_data["selected_date"],
            start_time=time_obj,
        )
        appt, error = appointment_repository.create_appointment(db, appt_create)

        if error:
            msg = f"⚠️ {error}\n¿En qué más puedo ayudarte?"
            await update.message.reply_text(msg, reply_markup=reply_markup)
            return MENU

        msg = (
            f"🎉 ¡Cita confirmada!\n\n"
            f"Tu cita para *{context.user_data['selected_service_name']}* "
            f"el *{context.user_data['selected_date']}* a las *{context.user_data['selected_time']}* "
            f"ha sido registrada con éxito.\n\n"
            f"ID de cita: #{appt.id}\n\n"
            "¿Algo más en lo que pueda ayudarte?"
        )

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)

    finally:
        db.close()

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    return MENU


# ── Ver mis citas ──────────────────────────────

async def show_my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        client_id = context.user_data.get("client_id")
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.client_id == client_id,
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )

        if not appointments:
            msg = "No tienes citas activas en este momento."
        else:
            lines = ["*📅 Tus citas próximas:*\n"]
            for a in appointments:
                service = db.query(Service).filter(Service.id == a.service_id).first()
                lines.append(
                    f"• #{a.id} – {service.name if service else 'Servicio'} – "
                    f"{a.appointment_date} {a.start_time.strftime('%H:%M')} – "
                    f"Estado: {a.status}"
                )
            msg = "\n".join(lines)

        await update.message.reply_text(msg, parse_mode="Markdown")

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)
    finally:
        db.close()

    return MENU


# ── Cancelar cita ──────────────────────────────

async def start_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    try:
        client_id = context.user_data.get("client_id")
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.client_id == client_id,
                Appointment.status.notin_(["cancelled", "completed"]),
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .limit(10)
            .all()
        )

        if not appointments:
            await update.message.reply_text("No tienes citas activas para cancelar.")
            return MENU

        lines = ["*¿Cuál cita deseas cancelar?*\n", "Escribe el ID de la cita:\n"]
        for a in appointments:
            service = db.query(Service).filter(Service.id == a.service_id).first()
            lines.append(
                f"• ID #{a.id} – {service.name if service else 'Servicio'} – "
                f"{a.appointment_date} {a.start_time.strftime('%H:%M')}"
            )
        msg = "\n".join(lines)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)
    finally:
        db.close()

    return CANCELLING_APPOINTMENT


async def cancel_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    keyboard = [
        ["1️⃣ Ver servicios", "2️⃣ Agendar cita"],
        ["3️⃣ Mis citas", "4️⃣ Cancelar cita"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    try:
        appt_id = int(text.replace("#", "").strip())
    except ValueError:
        await update.message.reply_text("Por favor escribe un ID numérico válido.", reply_markup=reply_markup)
        return MENU

    db = SessionLocal()
    try:
        client_id = context.user_data.get("client_id")
        appt = db.query(Appointment).filter(
            Appointment.id == appt_id,
            Appointment.client_id == client_id,
        ).first()

        if not appt:
            msg = f"No encontré la cita #{appt_id} o no te pertenece."
        elif appt.status in ("cancelled", "completed"):
            msg = f"La cita #{appt_id} ya está {appt.status}."
        else:
            appt.status = "cancelled"
            db.commit()
            msg = f"✅ La cita #{appt_id} ha sido cancelada."

        await update.message.reply_text(msg, reply_markup=reply_markup)

        conv_id = context.user_data.get("conversation_id")
        if conv_id:
            _save_message(conv_id, "outgoing", msg)
    finally:
        db.close()

    return MENU


# ── Fallback ──────────────────────────────

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        ["1️⃣ Ver servicios", "2️⃣ Agendar cita"],
        ["3️⃣ Mis citas", "4️⃣ Cancelar cita"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "No entendí eso. Por favor usa el menú:", reply_markup=reply_markup
    )
    return MENU


# ──────────────────────────────────────────────
# Punto de entrada
# ──────────────────────────────────────────────

def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN no está definido en el archivo .env. "
            "Agrega TELEGRAM_BOT_TOKEN=<tu_token> al archivo .env y vuelve a ejecutar."
        )
        sys.exit(1)

    # Asegurar tablas creadas
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

    logger.info("Bot de Turnix iniciado. Esperando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
