"""Proteccion de tokens de bots de Telegram por tenant."""
import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

PLACEHOLDER_KEYS = {"", "your_encryption_key_here", "changeme"}


def _is_placeholder(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in PLACEHOLDER_KEYS


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw_key = (settings.TELEGRAM_TOKEN_ENCRYPTION_KEY or "").strip()
    if _is_placeholder(raw_key):
        logger.warning(
            "TELEGRAM_TOKEN_ENCRYPTION_KEY no esta configurada; se usara una clave de desarrollo derivada."
        )
        raw_key = settings.SECRET_KEY

    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    """Cifra un token de Telegram sin registrarlo ni devolverlo plano."""
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Descifra un token guardado. Retorna None si no se puede descifrar."""
    if not encrypted_token:
        return None
    try:
        return _fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("No se pudo descifrar un token de Telegram guardado.")
        return None


def mask_token(token: Optional[str]) -> Optional[str]:
    """Devuelve una version segura para UI, por ejemplo 857813****QSA1Xc."""
    if not token:
        return None
    compact = token.strip()
    if len(compact) <= 10:
        return f"{compact[:2]}****{compact[-2:]}"
    return f"{compact[:6]}****{compact[-6:]}"
