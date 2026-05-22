"""Local worker for Premium Telegram appointment reminders.

Usage:
  python -m app.services.reminder_worker
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import joinedload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, create_tables
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.service import Service
from app.models.telegram_config import TelegramConfig
from app.models.tenant import Tenant
from app.services.telegram_token_service import decrypt_token

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TELEGRAM_SEND_MESSAGE = "https://api.telegram.org/bot{token}/sendMessage"
POLL_SECONDS = 60
DRY_RUN = os.getenv("TURNIX_REMINDER_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
RUN_ONCE = os.getenv("TURNIX_REMINDER_ONCE", "").strip().lower() in {"1", "true", "yes"}


class SafeDict(defaultdict):
    def __missing__(self, key):
        return "{" + key + "}"


def _format_message(template: Optional[str], values: dict[str, Any]) -> str:
    try:
        return (template or "").format_map(SafeDict(str, {k: "" if v is None else v for k, v in values.items()}))
    except Exception:
        return template or ""


def _values(tenant: Tenant, client: Client, service: Service, appointment: Appointment) -> dict[str, Any]:
    return {
        "business_name": tenant.name,
        "service_name": service.name if service else "",
        "date": str(appointment.appointment_date),
        "time": appointment.start_time.strftime("%H:%M"),
        "client_name": client.full_name if client else "",
        "phone": client.phone if client else "",
        "price": f"${int(service.price):,}" if service else "",
        "duration": f"{service.duration_minutes} min" if service else "",
    }


def _appointment_datetime(appointment: Appointment) -> datetime:
    return datetime.combine(appointment.appointment_date, appointment.start_time)


def _conversation_for(db, appointment: Appointment, config: TelegramConfig) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == appointment.tenant_id,
            Conversation.client_id == appointment.client_id,
            Conversation.bot_id == config.bot_id,
            Conversation.channel == "telegram",
        )
        .order_by(Conversation.last_interaction_at.desc())
        .first()
    )


def _send_message(token: str, chat_id: str, text: str) -> bool:
    if DRY_RUN:
        logger.info("DRY_RUN: recordatorio preparado para chat %s.", chat_id)
        return True
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(TELEGRAM_SEND_MESSAGE.format(token=token), json={"chat_id": chat_id, "text": text})
        result = response.json()
        return bool(result.get("ok"))
    except Exception:
        logger.exception("No se pudo enviar un recordatorio por Telegram.")
        return False


def _record_outgoing(db, conversation: Conversation, content: str) -> None:
    conversation.last_interaction_at = datetime.now(timezone.utc)
    db.add(Message(conversation_id=conversation.id, direction="outgoing", content=content))


def _process_once() -> int:
    db = SessionLocal()
    sent = 0
    try:
        now = datetime.now()
        horizon = now + timedelta(minutes=31)
        appointments = (
            db.query(Appointment)
            .options(
                joinedload(Appointment.tenant).joinedload(Tenant.plan),
                joinedload(Appointment.client),
                joinedload(Appointment.service),
            )
            .filter(
                Appointment.status.in_(["pending", "confirmed"]),
                Appointment.appointment_date >= now.date(),
                Appointment.appointment_date <= horizon.date(),
            )
            .all()
        )

        for appointment in appointments:
            tenant = appointment.tenant
            if not tenant or not tenant.plan or not tenant.plan.allows_advanced_reminders:
                continue
            config = (
                db.query(TelegramConfig)
                .filter(
                    TelegramConfig.tenant_id == tenant.id,
                    TelegramConfig.is_connected == True,
                    TelegramConfig.bot_token_encrypted.isnot(None),
                )
                .first()
            )
            if not config or not appointment.client or not appointment.client.telegram_user_id:
                continue
            token = decrypt_token(config.bot_token_encrypted)
            if not token:
                continue
            conversation = _conversation_for(db, appointment, config)
            if not conversation:
                continue

            appointment_dt = _appointment_datetime(appointment)
            minutes_until = (appointment_dt - now).total_seconds() / 60
            reminders = [
                (
                    "reminder_30_sent_at",
                    30,
                    config.reminder_30_message
                    or "Te recordamos que tienes una cita en {business_name} a las {time}. Te esperamos.",
                ),
                (
                    "reminder_15_sent_at",
                    15,
                    config.reminder_15_message
                    or "Tu cita en {business_name} será en 15 minutos. Gracias por usar nuestro sistema de agendamiento.",
                ),
            ]
            for field_name, target_minutes, template in reminders:
                already_sent = getattr(appointment, field_name)
                in_window = target_minutes - 1 <= minutes_until <= target_minutes
                if already_sent or not in_window:
                    continue
                text = _format_message(template, _values(tenant, appointment.client, appointment.service, appointment))
                if _send_message(token, conversation.chat_id, text):
                    setattr(appointment, field_name, datetime.now(timezone.utc))
                    _record_outgoing(db, conversation, text)
                    sent += 1

        db.commit()
        return sent
    except Exception:
        db.rollback()
        logger.exception("Error procesando recordatorios.")
        return sent
    finally:
        db.close()


async def run_forever() -> None:
    create_tables()
    print("Iniciando worker de recordatorios Premium...")
    if RUN_ONCE:
        sent = _process_once()
        print(f"Revisión de recordatorios completada. Recordatorios preparados/enviados: {sent}")
        return
    while True:
        sent = _process_once()
        if sent:
            logger.info("Recordatorios enviados: %s", sent)
        await asyncio.sleep(POLL_SECONDS)


def main() -> None:
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        print("Worker de recordatorios detenido.")


if __name__ == "__main__":
    main()

