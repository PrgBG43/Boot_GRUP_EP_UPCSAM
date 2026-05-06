"""Configuración de Telegram por tenant."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Mensajes personalizables del bot
    welcome_message = Column(Text, nullable=True, default="👋 ¡Bienvenido! ¿En qué puedo ayudarte?")
    services_message = Column(Text, nullable=True, default="Estos son nuestros servicios disponibles:")
    ask_date_message = Column(Text, nullable=True, default="¿Para qué fecha deseas tu cita? (YYYY-MM-DD)")
    ask_time_message = Column(Text, nullable=True, default="Selecciona el horario disponible:")
    confirm_message  = Column(Text, nullable=True, default="✅ ¡Cita confirmada! Te esperamos.")
    cancel_message   = Column(Text, nullable=True, default="❌ Tu cita ha sido cancelada.")

    # Opciones de comportamiento
    allow_cancellation = Column(Boolean, default=True)
    show_prices       = Column(Boolean, default=True)
    show_duration     = Column(Boolean, default=True)

    # Bot propio opcional (Opción B — para uso avanzado)
    # Guardado hasheado para no exponer el token
    bot_token_hint    = Column(String, nullable=True)  # últimos 6 chars del token para identificar
    use_global_bot    = Column(Boolean, default=True)   # True = usa el bot global de Turnix

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    tenant = relationship("Tenant", back_populates="telegram_config")
