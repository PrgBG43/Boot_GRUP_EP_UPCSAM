"""Configuracion de bots de Telegram por negocio."""
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import require_tenant_admin_or_above
from app.core.database import get_db
from app.models.telegram_config import TelegramConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.telegram_config import (
    TelegramConfigResponse,
    TelegramConfigUpdate,
    TelegramConnectRequest,
    TelegramConnectionResponse,
    TelegramPublicLinkResponse,
)
from app.services.telegram_token_service import decrypt_token, encrypt_token, mask_token

router = APIRouter()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _get_tenant_id(current_user: User, tenant_id_param: Optional[int] = None) -> int:
    if current_user.primary_role == "superadmin":
        if not tenant_id_param:
            raise HTTPException(status_code=400, detail="Superadmin debe especificar tenant_id.")
        return tenant_id_param
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="Usuario sin negocio asignado.")
    return current_user.tenant_id


def _get_or_create_config(db: Session, tenant_id: int) -> TelegramConfig:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Negocio no encontrado.")

    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant_id).first()
    if not config:
        config = TelegramConfig(tenant_id=tenant_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _public_link(config: TelegramConfig) -> Optional[str]:
    return f"https://t.me/{config.bot_username}" if config.bot_username else None


def _telegram_request(token: str, method: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10.0) as client:
            if payload is None:
                response = client.get(TELEGRAM_API.format(token=token, method=method))
            else:
                response = client.post(TELEGRAM_API.format(token=token, method=method), json=payload)
        return response.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo validar el bot con Telegram. Intenta nuevamente.",
        )


def _get_me(token: str) -> dict[str, Any]:
    result = _telegram_request(token, "getMe")
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token ingresado no es valido. Verifica el token entregado por BotFather.",
        )
    return result.get("result", {})


def _parse_commands(raw: Optional[str]) -> list[dict[str, str]]:
    if not raw:
        return []
    commands = []
    for line in raw.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if " - " in clean:
            command, description = clean.split(" - ", 1)
        elif ":" in clean:
            command, description = clean.split(":", 1)
        else:
            command, description = clean, clean.lstrip("/")
        command = command.strip().lstrip("/")
        description = description.strip()[:256] or command
        if command:
            commands.append({"command": command[:32], "description": description})
    return commands


def _sync_bot_profile(token: str, config: TelegramConfig) -> None:
    if config.bot_name:
        _telegram_request(token, "setMyName", {"name": config.bot_name[:64]})
    if config.bot_description is not None:
        _telegram_request(token, "setMyDescription", {"description": config.bot_description[:512]})
    if config.bot_short_description is not None:
        _telegram_request(
            token,
            "setMyShortDescription",
            {"short_description": config.bot_short_description[:120]},
        )
    commands = _parse_commands(config.bot_commands)
    if commands:
        _telegram_request(token, "setMyCommands", {"commands": commands})


def _telegram_upload_profile_photo(token: str, content: bytes, filename: str, content_type: str) -> None:
    payload = {"photo": '{"type":"static","photo":"attach://profile_photo"}'}
    files = {"profile_photo": (filename, content, content_type or "image/jpeg")}
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                TELEGRAM_API.format(token=token, method="setMyProfilePhoto"),
                data=payload,
                files=files,
            )
        result = response.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo actualizar la foto del bot con Telegram.",
        )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("description") or "Telegram no acepto la foto del bot.",
        )


def _telegram_remove_profile_photo(token: str) -> None:
    result = _telegram_request(token, "removeMyProfilePhoto")
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("description") or "Telegram no pudo quitar la foto del bot.",
        )


def _serialize(config: TelegramConfig) -> TelegramConfigResponse:
    return TelegramConfigResponse(
        id=config.id,
        tenant_id=config.tenant_id,
        is_connected=bool(config.is_connected),
        connection_status=config.connection_status or "not_connected",
        bot_id=config.bot_id,
        bot_username=config.bot_username,
        bot_name=config.bot_name,
        bot_description=config.bot_description,
        bot_short_description=config.bot_short_description,
        bot_commands=config.bot_commands,
        bot_token_masked=config.bot_token_masked,
        public_link=_public_link(config),
        last_validated_at=config.last_validated_at,
        welcome_message=config.welcome_message,
        services_message=config.services_message,
        ask_name_message=config.ask_name_message,
        ask_phone_message=config.ask_phone_message,
        ask_service_message=config.ask_service_message,
        ask_date_message=config.ask_date_message,
        ask_time_message=config.ask_time_message,
        confirm_message=config.confirm_message,
        cancel_message=config.cancel_message,
        unavailable_message=config.unavailable_message,
        goodbye_message=config.goodbye_message,
        plan_limit_public_message=config.plan_limit_public_message,
        reminder_30_message=config.reminder_30_message,
        reminder_15_message=config.reminder_15_message,
        allow_cancellation=bool(config.allow_cancellation),
        show_prices=bool(config.show_prices),
        show_duration=bool(config.show_duration),
        collect_phone=bool(config.collect_phone),
        require_confirmation=bool(config.require_confirmation),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/", response_model=TelegramConfigResponse)
def get_telegram_config(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    return _serialize(_get_or_create_config(db, tid))


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
    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    token = decrypt_token(config.bot_token_encrypted) if config.is_connected else None
    if token:
        _sync_bot_profile(token, config)
        config.connection_status = "connected"

    db.commit()
    db.refresh(config)
    return _serialize(config)


@router.post("/connect", response_model=TelegramConnectionResponse)
def connect_telegram_bot(
    payload: TelegramConnectRequest,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    token = payload.bot_token.strip()
    bot_info = _get_me(token)
    bot_id = str(bot_info.get("id"))

    existing = (
        db.query(TelegramConfig)
        .filter(
            TelegramConfig.bot_id == bot_id,
            TelegramConfig.tenant_id != tid,
            TelegramConfig.is_connected == True,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este bot ya esta conectado a otro negocio.")

    config = _get_or_create_config(db, tid)
    config.bot_token_encrypted = encrypt_token(token)
    config.bot_token_masked = mask_token(token)
    config.bot_id = bot_id
    config.bot_username = bot_info.get("username")
    config.bot_name = bot_info.get("first_name") or config.bot_name
    config.is_connected = True
    config.connection_status = "connected"
    config.last_validated_at = datetime.now(timezone.utc)

    _sync_bot_profile(token, config)

    db.commit()
    db.refresh(config)
    return TelegramConnectionResponse(
        is_connected=True,
        bot_username=config.bot_username,
        bot_name=config.bot_name,
        public_link=_public_link(config),
        bot_token_masked=config.bot_token_masked,
        last_validated_at=config.last_validated_at,
        connection_status=config.connection_status,
        message="Bot conectado correctamente.",
    )


@router.post("/disconnect", response_model=TelegramConfigResponse)
def disconnect_telegram_bot(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    config.bot_token_encrypted = None
    config.bot_token_masked = None
    config.bot_id = None
    config.bot_username = None
    config.bot_name = None
    config.is_connected = False
    config.connection_status = "not_connected"
    config.last_validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _serialize(config)


@router.post("/validate", response_model=TelegramConnectionResponse)
def validate_saved_telegram_bot(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    token = decrypt_token(config.bot_token_encrypted)
    if not token:
        config.is_connected = False
        config.connection_status = "not_connected"
        db.commit()
        raise HTTPException(status_code=400, detail="No hay un bot conectado para este negocio.")

    bot_info = _get_me(token)
    config.bot_id = str(bot_info.get("id"))
    config.bot_username = bot_info.get("username")
    config.bot_name = bot_info.get("first_name") or config.bot_name
    config.is_connected = True
    config.connection_status = "connected"
    config.last_validated_at = datetime.now(timezone.utc)
    _sync_bot_profile(token, config)
    db.commit()
    db.refresh(config)

    return TelegramConnectionResponse(
        is_connected=True,
        bot_username=config.bot_username,
        bot_name=config.bot_name,
        public_link=_public_link(config),
        bot_token_masked=config.bot_token_masked,
        last_validated_at=config.last_validated_at,
        connection_status=config.connection_status,
        message="Bot validado correctamente.",
    )


@router.get("/public-link", response_model=TelegramPublicLinkResponse)
def get_public_telegram_link(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    return TelegramPublicLinkResponse(
        is_connected=bool(config.is_connected),
        bot_username=config.bot_username,
        public_link=_public_link(config),
    )


@router.post("/profile-photo", response_model=TelegramConnectionResponse)
async def update_bot_profile_photo(
    tenant_id: int = None,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    token = decrypt_token(config.bot_token_encrypted)
    if not token or not config.is_connected:
        raise HTTPException(status_code=400, detail="Conecta el bot antes de actualizar la foto.")

    if photo.content_type not in {"image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Usa una imagen JPG.")
    content = await photo.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen debe pesar maximo 5 MB.")

    _telegram_upload_profile_photo(
        token,
        content,
        photo.filename or "profile-photo.jpg",
        photo.content_type or "image/jpeg",
    )
    config.last_validated_at = datetime.now(timezone.utc)
    config.connection_status = "connected"
    db.commit()
    db.refresh(config)
    return TelegramConnectionResponse(
        is_connected=True,
        bot_username=config.bot_username,
        bot_name=config.bot_name,
        public_link=_public_link(config),
        bot_token_masked=config.bot_token_masked,
        last_validated_at=config.last_validated_at,
        connection_status=config.connection_status,
        message="Foto del bot actualizada correctamente.",
    )


@router.delete("/profile-photo", response_model=TelegramConnectionResponse)
def remove_bot_profile_photo(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    token = decrypt_token(config.bot_token_encrypted)
    if not token or not config.is_connected:
        raise HTTPException(status_code=400, detail="Conecta el bot antes de quitar la foto.")
    _telegram_remove_profile_photo(token)
    config.last_validated_at = datetime.now(timezone.utc)
    config.connection_status = "connected"
    db.commit()
    db.refresh(config)
    return TelegramConnectionResponse(
        is_connected=True,
        bot_username=config.bot_username,
        bot_name=config.bot_name,
        public_link=_public_link(config),
        bot_token_masked=config.bot_token_masked,
        last_validated_at=config.last_validated_at,
        connection_status=config.connection_status,
        message="Foto del bot removida correctamente.",
    )
