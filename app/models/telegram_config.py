"""Configuración de Telegram por tenant."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class TelegramConfig(Base):
    __tablename__ = "telegram_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # ── Bot propio (Opción B) ─────────────────────────────────
    # SEGURIDAD: el token se guarda completo solo en la BD (nunca se expone en API ni consola)
    # En respuestas API se devuelve únicamente bot_token_masked (ej: 123456:ABC****XYZ)
    bot_token         = Column(String, nullable=True)  # token completo – solo lectura interna
    bot_token_masked  = Column(String, nullable=True)  # versión enmascarada para mostrar en UI
    bot_username      = Column(String, nullable=True)  # @username del bot (obtenido via getMe)
    bot_name          = Column(String, nullable=True)  # nombre visible del bot
    bot_description   = Column(String, nullable=True)  # descripción larga del bot
    bot_short_description = Column(String, nullable=True)  # descripción corta (hasta 120 chars)
    bot_profile_photo_path = Column(String, nullable=True)  # ruta local o URL de imagen de perfil
    use_global_bot    = Column(Boolean, default=True)   # True = usa el bot global de Turnix

    # Estado de conexión del bot
    # Valores: sin_configurar | conectado | token_invalido | error
    bot_status        = Column(String, nullable=True, default="sin_configurar")
    is_active         = Column(Boolean, default=False)   # True = bot activo para este tenant
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    # ── Mensajes personalizables ──────────────────────────────
    welcome_message      = Column(Text, nullable=True, default="👋 ¡Bienvenido! ¿En qué puedo ayudarte?")
    services_message     = Column(Text, nullable=True, default="Estos son nuestros servicios disponibles:")
    ask_date_message     = Column(Text, nullable=True, default="¿Para qué fecha deseas tu cita? (YYYY-MM-DD)")
    ask_time_message     = Column(Text, nullable=True, default="Selecciona el horario disponible:")
    confirm_message      = Column(Text, nullable=True, default="✅ ¡Cita confirmada! Te esperamos.")
    cancel_message       = Column(Text, nullable=True, default="❌ Tu cita ha sido cancelada.")
    unavailable_message  = Column(Text, nullable=True, default="😔 No hay horarios disponibles para esa fecha. Elige otra.")

    # ── Opciones de comportamiento ────────────────────────────
    allow_cancellation = Column(Boolean, default=True)
    show_prices        = Column(Boolean, default=True)
    show_duration      = Column(Boolean, default=True)

    # Nota: bot_token_hint se mantiene para retrocompatibilidad
    bot_token_hint     = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    tenant = relationship("Tenant", back_populates="telegram_config")
