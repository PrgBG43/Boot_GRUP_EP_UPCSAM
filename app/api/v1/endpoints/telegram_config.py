"""Configuración de bots de Telegram por negocio."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

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
STATIC_DIR = Path(__file__).resolve().parents[3] / "static"
TELEGRAM_LOGO_DIR = STATIC_DIR / "uploads" / "telegram-logos"
ALLOWED_COMMAND_ACTIONS = {
    "iniciar_agendamiento",
    "mostrar_servicios",
    "mostrar_horarios",
    "mostrar_citas_cliente",
    "cancelar_cita",
    "mostrar_ayuda",
    "respuesta_personalizada",
}
DEFAULT_COMMANDS: list[dict[str, Any]] = [
    {
        "command": "/start",
        "description": "Iniciar reservas",
        "action_type": "iniciar_agendamiento",
        "message": "Hola. Bienvenido a {business_name}. Vamos a agendar tu cita.",
        "is_active": True,
    },
    {
        "command": "/servicios",
        "description": "Ver servicios",
        "action_type": "mostrar_servicios",
        "message": "Estos son nuestros servicios disponibles:",
        "is_active": True,
    },
    {
        "command": "/horarios",
        "description": "Ver horarios disponibles",
        "action_type": "mostrar_horarios",
        "message": "Estos son los próximos horarios disponibles:",
        "is_active": True,
    },
    {
        "command": "/citas",
        "description": "Ver mis citas",
        "action_type": "mostrar_citas_cliente",
        "message": None,
        "is_active": True,
    },
    {
        "command": "/cancelar",
        "description": "Cancelar una cita",
        "action_type": "cancelar_cita",
        "message": "Vamos a revisar tus citas activas para cancelar la que elijas.",
        "is_active": True,
    },
    {
        "command": "/ayuda",
        "description": "Obtener ayuda",
        "action_type": "mostrar_ayuda",
        "message": "Puedes escribir /servicios para ver nuestros servicios o /start para agendar una cita.",
        "is_active": True,
    },
]


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
            detail="El token ingresado no es válido. Verifica el token entregado por BotFather.",
        )
    return result.get("result", {})


def _normalize_command(command: str) -> str:
    clean = (command or "").strip().lower()
    clean = clean if clean.startswith("/") else f"/{clean}"
    clean = re.sub(r"[^/a-z0-9_]", "", clean)
    return clean[:33]


def _command_from_dict(item: dict[str, Any]) -> dict[str, Any]:
    command = _normalize_command(str(item.get("command") or ""))
    if not command or command == "/":
        raise ValueError("command")
    description = (item.get("description") or command.lstrip("/")).strip()[:256]
    action_type = item.get("action_type") or "respuesta_personalizada"
    if action_type not in ALLOWED_COMMAND_ACTIONS:
        action_type = "respuesta_personalizada"
    return {
        "command": command,
        "description": description or command.lstrip("/"),
        "action_type": action_type,
        "message": (item.get("message") or "").strip() or None,
        "is_active": bool(item.get("is_active", True)),
    }


def _commands_from_text(raw: str) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
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
        command = _normalize_command(command)
        description = description.strip()[:256] or command.lstrip("/")
        if command:
            commands.append(
                {
                    "command": command,
                    "description": description,
                    "action_type": "respuesta_personalizada",
                    "message": None,
                    "is_active": True,
                }
            )
    return commands


def _normalize_commands(raw: Optional[Any]) -> list[dict[str, Any]]:
    if raw in (None, "", []):
        return [dict(item) for item in DEFAULT_COMMANDS]
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return [dict(item) for item in DEFAULT_COMMANDS]
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = _commands_from_text(stripped)
    else:
        parsed = raw

    commands: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in parsed or []:
        try:
            data = _command_from_dict(item if isinstance(item, dict) else item.model_dump())
        except Exception:
            continue
        if data["command"] in seen:
            continue
        seen.add(data["command"])
        commands.append(data)
    for item in DEFAULT_COMMANDS:
        if item["command"] not in seen:
            seen.add(item["command"])
            commands.append(dict(item))
    return commands or [dict(item) for item in DEFAULT_COMMANDS]


def _store_commands(commands: Any) -> str:
    return json.dumps(_normalize_commands(commands), ensure_ascii=False)


def _telegram_commands(config: TelegramConfig) -> list[dict[str, str]]:
    return [
        {
            "command": item["command"].lstrip("/")[:32],
            "description": item["description"][:256],
        }
        for item in _normalize_commands(config.bot_commands)
        if item.get("is_active")
    ]


def _internal_logo_url(config: TelegramConfig) -> Optional[str]:
    if not config.internal_logo_path:
        return None
    return f"/static/{config.internal_logo_path.lstrip('/')}"


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
    commands = _telegram_commands(config)
    if commands:
        _telegram_request(token, "setMyCommands", {"commands": commands})
    else:
        _telegram_request(token, "deleteMyCommands")


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
            detail="No se pudo actualizar la foto del bot con Telegram. Intenta nuevamente.",
        )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("description") or "Telegram no aceptó la foto del bot.",
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
        bot_commands=_normalize_commands(config.bot_commands),
        bot_token_masked=config.bot_token_masked,
        public_link=_public_link(config),
        internal_logo_url=_internal_logo_url(config),
        internal_logo_updated_at=config.internal_logo_updated_at,
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
        auto_start_on_greeting=bool(config.auto_start_on_greeting),
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
        if key == "bot_commands":
            config.bot_commands = _store_commands(value)
        elif hasattr(config, key):
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este bot ya está conectado a otro negocio.")

    config = _get_or_create_config(db, tid)
    config.bot_token_encrypted = encrypt_token(token)
    config.bot_token_masked = mask_token(token)
    config.bot_id = bot_id
    config.bot_username = bot_info.get("username")
    config.bot_name = bot_info.get("first_name") or config.bot_name
    config.bot_commands = config.bot_commands or _store_commands(DEFAULT_COMMANDS)
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


def _safe_logo_suffix(filename: Optional[str], content_type: Optional[str]) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type or "", ".jpg")


def _delete_internal_logo(path: Optional[str]) -> None:
    if not path:
        return
    target = (STATIC_DIR / path).resolve()
    logo_root = TELEGRAM_LOGO_DIR.resolve()
    try:
        target.relative_to(logo_root)
    except ValueError:
        return
    if target.exists():
        target.unlink()


@router.post("/internal-logo", response_model=TelegramConfigResponse)
async def update_internal_logo(
    tenant_id: int = None,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)

    allowed_types = {"image/jpeg", "image/jpg"}
    if logo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Usa una imagen JPG para actualizar la foto del bot.")

    content = await logo.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen debe pesar máximo 5 MB.")

    TELEGRAM_LOGO_DIR.mkdir(parents=True, exist_ok=True)
    old_path = config.internal_logo_path
    suffix = _safe_logo_suffix(logo.filename, logo.content_type)
    filename = f"tenant-{tid}-{uuid4().hex}{suffix}"
    relative_path = f"uploads/telegram-logos/{filename}"
    target = TELEGRAM_LOGO_DIR / filename
    target.write_bytes(content)

    token = decrypt_token(config.bot_token_encrypted)
    if token and config.is_connected:
        try:
            _telegram_upload_profile_photo(
                token,
                content,
                logo.filename or "profile-photo.jpg",
                logo.content_type or "image/jpeg",
            )
        except Exception:
            target.unlink(missing_ok=True)
            raise

    config.internal_logo_path = relative_path
    config.internal_logo_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    _delete_internal_logo(old_path)
    return _serialize(config)


@router.delete("/internal-logo", response_model=TelegramConfigResponse)
def remove_internal_logo(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    tid = _get_tenant_id(current_user, tenant_id)
    config = _get_or_create_config(db, tid)
    old_path = config.internal_logo_path
    token = decrypt_token(config.bot_token_encrypted)
    if token and config.is_connected:
        _telegram_remove_profile_photo(token)
    config.internal_logo_path = None
    config.internal_logo_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    _delete_internal_logo(old_path)
    return _serialize(config)


# Compatibilidad con el frontend anterior: ahora esta ruta guarda solo el logo interno.
@router.post("/profile-photo", response_model=TelegramConfigResponse)
async def update_bot_profile_photo(
    tenant_id: int = None,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    return await update_internal_logo(tenant_id=tenant_id, logo=photo, db=db, current_user=current_user)


@router.delete("/profile-photo", response_model=TelegramConfigResponse)
def remove_bot_profile_photo(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    return remove_internal_logo(tenant_id=tenant_id, db=db, current_user=current_user)
