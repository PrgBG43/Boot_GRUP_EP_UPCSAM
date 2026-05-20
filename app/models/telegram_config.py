"""Configuración de Telegram por negocio."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Futuro modo avanzado: bot propio por negocio.
    # El runtime productivo usa el bot global de Turnix con /start <slug>.
    bot_token = Column(String, nullable=True)
    bot_token_masked = Column(String, nullable=True)
    bot_username = Column(String, nullable=True)
    bot_name = Column(String, nullable=True)
    bot_description = Column(String, nullable=True)
    bot_short_description = Column(String, nullable=True)
    bot_profile_photo_path = Column(String, nullable=True)
    use_global_bot = Column(Boolean, default=True)

    bot_status = Column(String, nullable=True, default="sin_configurar")
    is_active = Column(Boolean, default=False)
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    welcome_message = Column(Text, nullable=True, default="Bienvenido. ¿En qué puedo ayudarte?")
    services_message = Column(Text, nullable=True, default="Estos son nuestros servicios disponibles:")
    ask_date_message = Column(Text, nullable=True, default="¿Para qué fecha deseas tu cita? (YYYY-MM-DD)")
    ask_time_message = Column(Text, nullable=True, default="Selecciona el horario disponible:")
    confirm_message = Column(Text, nullable=True, default="Tu cita ha sido confirmada. Te esperamos.")
    cancel_message = Column(Text, nullable=True, default="Tu cita ha sido cancelada.")
    unavailable_message = Column(Text, nullable=True, default="No hay horarios disponibles para esa fecha. Elige otra.")

    allow_cancellation = Column(Boolean, default=True)
    show_prices = Column(Boolean, default=True)
    show_duration = Column(Boolean, default=True)
    bot_token_hint = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    tenant = relationship("Tenant", back_populates="telegram_config")
