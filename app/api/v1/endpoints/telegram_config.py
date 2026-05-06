"""Configuración de Telegram por negocio."""
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_tenant_admin_or_above
from app.models.user import User
from app.models.telegram_config import TelegramConfig
from app.schemas.telegram_config import (
    TelegramConfigResponse,
    TelegramConfigUpdate,
    TelegramValidateRequest,
    TelegramValidateResponse,
)

router = APIRouter()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _mask_token(token: str) -> str:
    """Devuelve versión enmascarada: '123456:ABC****XYZ'."""
    if not token or ":" not in token:
        return "***:***"
    prefix, secret = token.split(":", 1)
    if len(secret) <= 8:
        return f"{prefix}:***"
    return f"{prefix}:{secret[:3]}{'*' * (len(secret) - 6)}{secret[-3:]}"


def _get_tenant_id(current_user: User, tenant_id_param: int = None) -> int:
    if current_user.primary_role == "superadmin":
        if not tenant_id_param:
            raise HTTPException(status_code=400, detail="Superadmin debe especificar tenant_id")
        return tenant_id_param
    return current_user.tenant_id


def _get_or_create_config(db: Session, tid: int) -> TelegramConfig:
    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tid).first()
    if not config:
        config = TelegramConfig(tenant_id=tid)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/", response_model=TelegramConfigResponse)
def get_telegram_config(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Obtiene la configuración de Telegram del negocio."""
    tid = _get_tenant_id(current_user, tenant_id)
    return _get_or_create_config(db, tid)


@router.put("/", response_model=TelegramConfigResponse)
def update_telegram_config(
    config_in: TelegramConfigUpdate,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Actualiza la configuración de Telegram del negocio.
    Si se incluye bot_token, se guarda internamente y se calcula la versión enmascarada.
    El bot_token NUNCA se devuelve en la respuesta.
    """
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)

    data = config_in.model_dump(exclude_unset=True)

    # Tratar bot_token por separado – guardar pero no devolver
    raw_token = data.pop("bot_token", None)
    if raw_token is not None:
        if raw_token.strip() == "":
            # Limpiar token
            config.bot_token = None
            config.bot_token_masked = None
            config.bot_token_hint = None
            config.bot_status = "sin_configurar"
            config.is_active = False
        else:
            config.bot_token = raw_token.strip()
            config.bot_token_masked = _mask_token(raw_token.strip())
            # Mantener bot_token_hint por retrocompatibilidad (últimos 6 chars)
            config.bot_token_hint = raw_token.strip()[-6:] if len(raw_token.strip()) > 6 else raw_token.strip()

    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


@router.post("/validate", response_model=TelegramValidateResponse)
def validate_telegram_token(
    payload: TelegramValidateRequest,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Valida un token de Telegram llamando a getMe.
    Si es válido, actualiza bot_username, bot_name y estado de la configuración.
    SEGURIDAD: el token no se registra en logs ni se devuelve.
    """
    tid = _get_tenant_id(current_user, tenant_id)
    token = payload.bot_token.strip()

    # Validar formato básico del token (no ejecutar si no parece token válido)
    if not re.match(r"^\d+:[A-Za-z0-9_-]{35,}$", token):
        return TelegramValidateResponse(
            ok=False,
            status="token_invalido",
            message="Formato de token incorrecto. Debe ser: NÚMERO:CARACTERES_ALFANUMÉRICOS",
        )

    try:
        url = TELEGRAM_API.format(token=token, method="getMe")
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        result = resp.json()
    except Exception as e:
        return TelegramValidateResponse(
            ok=False,
            status="error",
            message=f"No se pudo conectar con Telegram: {type(e).__name__}",
        )

    if not result.get("ok"):
        # Guardar estado de error en config
        config = _get_or_create_config(db, tid)
        config.bot_status = "token_invalido"
        config.last_validated_at = datetime.now(timezone.utc)
        db.commit()
        return TelegramValidateResponse(
            ok=False,
            status="token_invalido",
            message="Token rechazado por Telegram. Verifica que sea correcto y no esté revocado.",
        )

    bot_info = result.get("result", {})
    bot_username = bot_info.get("username")
    bot_name = bot_info.get("first_name")

    # Actualizar configuración con datos del bot
    config = _get_or_create_config(db, tid)
    config.bot_token = token
    config.bot_token_masked = _mask_token(token)
    config.bot_token_hint = token[-6:] if len(token) > 6 else token
    config.bot_username = bot_username
    config.bot_name = bot_name or config.bot_name
    config.bot_status = "conectado"
    config.is_active = True
    config.use_global_bot = False
    config.last_validated_at = datetime.now(timezone.utc)
    db.commit()

    return TelegramValidateResponse(
        ok=True,
        bot_username=bot_username,
        bot_name=bot_name,
        status="conectado",
        message=f"✅ Bot conectado correctamente: @{bot_username}",
    )
