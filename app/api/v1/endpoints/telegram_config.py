"""Configuración de Telegram por negocio."""
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_tenant_admin_or_above
from app.core.config import settings
from app.core.database import get_db
from app.core.slug import ensure_unique_slug
from app.models.telegram_config import TelegramConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.telegram_config import (
    TelegramConfigResponse,
    TelegramPublicLinkResponse,
    TelegramConfigUpdate,
    TelegramValidateRequest,
    TelegramValidateResponse,
)

router = APIRouter()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _mask_token(token: str) -> str:
    if not token or ":" not in token:
        return "***:***"
    prefix, secret = token.split(":", 1)
    if len(secret) <= 8:
        return f"{prefix}:***"
    return f"{prefix}:{secret[:3]}{'*' * (len(secret) - 6)}{secret[-3:]}"


def _get_tenant_id(current_user: User, tenant_id_param: int = None) -> int:
    if current_user.primary_role == "superadmin":
        if not tenant_id_param:
            raise HTTPException(status_code=400, detail="Superadmin debe especificar tenant_id.")
        return tenant_id_param
    return current_user.tenant_id


def _get_or_create_config(db: Session, tenant_id: int) -> TelegramConfig:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Negocio no encontrado.")

    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant_id).first()
    if not config:
        config = TelegramConfig(tenant_id=tenant_id, use_global_bot=True)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _ensure_tenant_slug(db: Session, tenant: Tenant) -> str:
    if tenant.slug:
        return tenant.slug
    tenant.slug = ensure_unique_slug(db, tenant.name, exclude_tenant_id=tenant.id)
    db.commit()
    db.refresh(tenant)
    return tenant.slug


def _global_bot_username() -> str | None:
    username = settings.TELEGRAM_BOT_USERNAME
    if username:
        return username.lstrip("@")
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            url = TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN, method="getMe")
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
            result = response.json()
            if result.get("ok"):
                return result.get("result", {}).get("username")
        except Exception:
            return None
    return None


def _serialize_config(db: Session, config: TelegramConfig) -> TelegramConfigResponse:
    tenant = db.query(Tenant).filter(Tenant.id == config.tenant_id).first()
    tenant_slug = _ensure_tenant_slug(db, tenant) if tenant else None
    global_username = _global_bot_username()
    bot_username = global_username if config.use_global_bot else config.bot_username
    public_link = None
    if bot_username and tenant_slug:
        public_link = f"https://t.me/{bot_username}?start={tenant_slug}"

    status = config.bot_status
    is_active = config.is_active
    if config.use_global_bot:
        status = "conectado" if global_username and settings.TELEGRAM_BOT_TOKEN else "sin_configurar"
        is_active = bool(global_username and settings.TELEGRAM_BOT_TOKEN)

    return TelegramConfigResponse(
        id=config.id,
        tenant_id=config.tenant_id,
        tenant_slug=tenant_slug,
        welcome_message=config.welcome_message,
        services_message=config.services_message,
        ask_date_message=config.ask_date_message,
        ask_time_message=config.ask_time_message,
        confirm_message=config.confirm_message,
        cancel_message=config.cancel_message,
        unavailable_message=config.unavailable_message,
        allow_cancellation=config.allow_cancellation,
        show_prices=config.show_prices,
        show_duration=config.show_duration,
        use_global_bot=config.use_global_bot,
        bot_name=config.bot_name,
        bot_description=config.bot_description,
        bot_short_description=config.bot_short_description,
        bot_username=bot_username,
        global_bot_username=global_username,
        public_bot_link=public_link,
        bot_status=status,
        is_active=is_active,
        last_validated_at=config.last_validated_at,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _build_public_link(db: Session, tenant_id: int) -> TelegramPublicLinkResponse:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Negocio no encontrado.")

    business_slug = _ensure_tenant_slug(db, tenant)
    bot_username = _global_bot_username()
    public_link = f"https://t.me/{bot_username}?start={business_slug}" if bot_username else None
    return TelegramPublicLinkResponse(
        bot_username=bot_username,
        business_slug=business_slug,
        public_link=public_link,
    )


@router.get("/", response_model=TelegramConfigResponse)
def get_telegram_config(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    return _serialize_config(db, config)


@router.put("/", response_model=TelegramConfigResponse)
def update_telegram_config(
    config_in: TelegramConfigUpdate,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)

    data = config_in.model_dump(exclude_unset=True)
    raw_token = data.pop("bot_token", None)
    if raw_token is not None:
        token = raw_token.strip()
        if token:
            config.bot_token = token
            config.bot_token_masked = _mask_token(token)
            config.bot_token_hint = token[-6:] if len(token) > 6 else token
        else:
            config.bot_token = None
            config.bot_token_masked = None
            config.bot_token_hint = None
            config.bot_status = "sin_configurar"
            config.is_active = False

    # El flujo entregado usa bot global + slug. Mantener True evita prometer multi-bot.
    data["use_global_bot"] = True

    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return _serialize_config(db, config)


@router.get("/public-link", response_model=TelegramPublicLinkResponse)
def get_public_telegram_link(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    return _build_public_link(db, tid)


@router.post("/validate", response_model=TelegramValidateResponse)
def validate_telegram_token(
    payload: TelegramValidateRequest,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Valida un token de Telegram llamando a getMe.

    Este endpoint se conserva como modo avanzado/futuro. El runtime productivo
    incluido usa TELEGRAM_BOT_TOKEN global y resuelve negocios por slug.
    """
    tid = _get_tenant_id(current_user, tenant_id)
    token = payload.bot_token.strip()

    if not re.match(r"^\d+:[A-Za-z0-9_-]{35,}$", token):
        return TelegramValidateResponse(
            ok=False,
            status="token_invalido",
            message="Formato de token incorrecto.",
        )

    try:
        url = TELEGRAM_API.format(token=token, method="getMe")
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        result = resp.json()
    except Exception as exc:
        return TelegramValidateResponse(
            ok=False,
            status="error",
            message=f"No se pudo conectar con Telegram: {type(exc).__name__}",
        )

    config = _get_or_create_config(db, tid)
    config.last_validated_at = datetime.now(timezone.utc)

    if not result.get("ok"):
        config.bot_status = "token_invalido"
        db.commit()
        return TelegramValidateResponse(
            ok=False,
            status="token_invalido",
            message="Token rechazado por Telegram. Verifica que sea correcto y no esté revocado.",
        )

    bot_info = result.get("result", {})
    bot_username = bot_info.get("username")
    bot_name = bot_info.get("first_name")

    config.bot_token = token
    config.bot_token_masked = _mask_token(token)
    config.bot_token_hint = token[-6:] if len(token) > 6 else token
    config.bot_username = bot_username
    config.bot_name = bot_name or config.bot_name
    config.bot_status = "conectado"
    config.is_active = True
    config.use_global_bot = True
    db.commit()

    return TelegramValidateResponse(
        ok=True,
        bot_username=bot_username,
        bot_name=bot_name,
        status="conectado",
        message=f"Bot validado correctamente: @{bot_username}. El runtime incluido usa el bot global de Turnix.",
    )
