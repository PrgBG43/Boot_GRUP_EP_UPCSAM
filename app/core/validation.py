"""Validadores compartidos de dominio."""
import re
from typing import Optional

PHONE_ERROR = "El teléfono debe tener 10 dígitos y comenzar por 3."
CO_MOBILE_RE = re.compile(r"^3[0-9]{9}$")


def validate_colombian_mobile(
    value: Optional[str],
    *,
    required: bool = False,
) -> Optional[str]:
    """Valida teléfono móvil colombiano estricto: 10 dígitos y comienza por 3."""
    if value is None:
        if required:
            raise ValueError(PHONE_ERROR)
        return None

    phone = value.strip()
    if not phone:
        if required:
            raise ValueError(PHONE_ERROR)
        return None

    if not CO_MOBILE_RE.fullmatch(phone):
        raise ValueError(PHONE_ERROR)
    return phone

