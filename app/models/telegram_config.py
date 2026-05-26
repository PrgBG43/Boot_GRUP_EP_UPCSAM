"""Configuración de Telegram por negocio."""
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
    internal_logo_path = Column(String, nullable=True)
    internal_logo_updated_at = Column(DateTime(timezone=True), nullable=True)

    is_connected = Column(Boolean, default=False)
    connection_status = Column(String, nullable=True, default="not_connected")
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    listener_status = Column(String, nullable=True, default="inactive")
    listener_started_at = Column(DateTime(timezone=True), nullable=True)
    last_message_received_at = Column(DateTime(timezone=True), nullable=True)
    last_bot_error = Column(Text, nullable=True)

    welcome_message = Column(
        Text,
        nullable=True,
        default="Bienvenido a {business_name}. Soy el asistente virtual de reservas.",
    )
    services_message = Column(Text, nullable=True, default="Estos son nuestros servicios disponibles:")
    ask_name_message = Column(Text, nullable=True, default="Por favor, escribe tu nombre completo.")
    ask_phone_message = Column(Text, nullable=True, default="Escribe tu número de celular para confirmar la cita.")
    ask_service_message = Column(Text, nullable=True, default="Selecciona el servicio que deseas agendar.")
    ask_date_message = Column(Text, nullable=True, default="¿Cuándo quieres agendar tu cita?")
    ask_time_message = Column(Text, nullable=True, default="Selecciona el horario disponible:")
    confirm_message = Column(
        Text,
        nullable=True,
        default="Tu cita para {service_name} fue registrada para el {date} a las {time}.",
    )
    cancel_message = Column(Text, nullable=True, default="Tu cita ha sido cancelada.")
    cancel_start_message = Column(Text, nullable=True, default="Voy a ayudarte a cancelar una cita.")
    cancel_no_appointments_message = Column(
        Text,
        nullable=True,
        default=(
            "No encontré citas activas para cancelar. "
            "Si necesitas ayuda, comunícate directamente con el negocio."
        ),
    )
    cancel_select_message = Column(
        Text,
        nullable=True,
        default="Encontré varias citas activas. Selecciona cuál deseas cancelar.",
    )
    cancel_confirm_message = Column(
        Text,
        nullable=True,
        default="¿Confirmas que deseas cancelar la cita de {service_name} del {date} a las {time}?",
    )
    cancel_success_message = Column(Text, nullable=True, default="Tu cita fue cancelada correctamente.")
    cancel_rejected_message = Column(Text, nullable=True, default="Perfecto, tu cita se mantiene activa.")
    cancellation_disabled_message = Column(
        Text,
        nullable=True,
        default=(
            "Este negocio no tiene habilitada la cancelación por Telegram. "
            "Comunícate directamente con el establecimiento para recibir ayuda."
        ),
    )
    unavailable_message = Column(Text, nullable=True, default="No hay horarios disponibles para esa fecha. Elige otra.")
    goodbye_message = Column(Text, nullable=True, default="Gracias por contactarnos. Te esperamos.")
    plan_limit_public_message = Column(
        Text,
        nullable=True,
        default=(
            "En este momento el negocio no está disponible para recibir nuevas citas por este medio. "
            "Intenta más tarde o comunícate directamente con el establecimiento."
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
            "Tu cita en {business_name} será en 15 minutos. "
            "Gracias por usar nuestro sistema de agendamiento."
        ),
    )

    allow_cancellation = Column(Boolean, default=True)
    auto_start_on_greeting = Column(Boolean, default=False)
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
