"""Configuracion de Telegram por negocio."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    bot_token_encrypted = Column(Text, nullable=True)
    bot_token_masked = Column(String, nullable=True)
    bot_id = Column(String, nullable=True, index=True)
    bot_username = Column(String, nullable=True)
    bot_name = Column(String, nullable=True)
    bot_description = Column(String, nullable=True)
    bot_short_description = Column(String, nullable=True)
    bot_commands = Column(Text, nullable=True)

    is_connected = Column(Boolean, default=False)
    connection_status = Column(String, nullable=True, default="not_connected")
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    welcome_message = Column(
        Text,
        nullable=True,
        default="Bienvenido a {business_name}. Soy el asistente virtual de reservas.",
    )
    services_message = Column(Text, nullable=True, default="Estos son nuestros servicios disponibles:")
    ask_name_message = Column(Text, nullable=True, default="Por favor, escribe tu nombre completo.")
    ask_phone_message = Column(Text, nullable=True, default="Escribe tu numero de celular para confirmar la cita.")
    ask_service_message = Column(Text, nullable=True, default="Selecciona el servicio que deseas agendar.")
    ask_date_message = Column(Text, nullable=True, default="Para que fecha deseas tu cita? (YYYY-MM-DD)")
    ask_time_message = Column(Text, nullable=True, default="Selecciona el horario disponible:")
    confirm_message = Column(
        Text,
        nullable=True,
        default="Tu cita para {service_name} fue registrada para el {date} a las {time}.",
    )
    cancel_message = Column(Text, nullable=True, default="Tu cita ha sido cancelada.")
    unavailable_message = Column(Text, nullable=True, default="No hay horarios disponibles para esa fecha. Elige otra.")
    goodbye_message = Column(Text, nullable=True, default="Gracias por contactarnos. Te esperamos.")
    plan_limit_public_message = Column(
        Text,
        nullable=True,
        default=(
            "En este momento el negocio no esta disponible para recibir nuevas citas por este medio. "
            "Intenta mas tarde o comunicate directamente con el establecimiento."
        ),
    )
    reminder_30_message = Column(
        Text,
        nullable=True,
        default="Te recordamos que tienes una cita en {business_name} a las {time}. Te esperamos.",
    )
    reminder_15_message = Column(
        Text,
        nullable=True,
        default=(
            "Tu cita en {business_name} sera en 15 minutos. "
            "Gracias por usar nuestro sistema de agendamiento."
        ),
    )

    allow_cancellation = Column(Boolean, default=True)
    show_prices = Column(Boolean, default=True)
    show_duration = Column(Boolean, default=True)
    collect_phone = Column(Boolean, default=True)
    require_confirmation = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    tenant = relationship("Tenant", back_populates="telegram_config")
