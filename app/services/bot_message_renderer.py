from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Mapping, Optional


BOT_MESSAGE_DEFAULTS: dict[str, str] = {
    "business_name": "el negocio",
    "client_name": "cliente",
    "service_name": "el servicio",
    "date": "la fecha seleccionada",
    "time": "la hora seleccionada",
    "phone": "No especificado",
    "price": "No especificado",
    "duration": "No especificada",
    "bot_name": "asistente virtual",
    "business_phone": "No especificado",
    "business_address": "No especificada",
    "appointment_status": "Pendiente",
}

APPOINTMENT_STATUS_LABELS = {
    "pending": "Pendiente",
    "confirmed": "Confirmada",
    "cancelled": "Cancelada",
    "completed": "Completada",
    "no_show": "No asistió",
}


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default) if obj is not None else default


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        clean = value.strip()
        try:
            return datetime.strptime(clean, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return clean
    return str(value)


def _format_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value).strip()


def _format_price(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        amount = Decimal(str(value))
        return f"${int(amount):,}".replace(",", ".")
    except Exception:
        return str(value).strip()


def _format_duration(value: Any) -> str:
    if value in (None, ""):
        return ""
    raw = str(value).strip()
    if raw.isdigit():
        minutes = int(raw)
        return f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos"
    return raw


def _normalize_value(key: str, value: Any) -> str:
    if value in (None, ""):
        return BOT_MESSAGE_DEFAULTS[key]
    if key == "date":
        return _format_date(value)
    if key == "time":
        return _format_time(value)
    if key == "price":
        return _format_price(value) or BOT_MESSAGE_DEFAULTS[key]
    if key == "duration":
        return _format_duration(value) or BOT_MESSAGE_DEFAULTS[key]
    if key == "appointment_status":
        return APPOINTMENT_STATUS_LABELS.get(str(value).strip().lower(), str(value).strip())
    return str(value).strip()


def render_bot_message(template: Optional[str], context: Optional[Mapping[str, Any]] = None) -> str:
    values = context or {}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in BOT_MESSAGE_DEFAULTS:
            return _normalize_value(key, values.get(key))
        value = values.get(key)
        return str(value).strip() if value not in (None, "") else match.group(0)

    rendered = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, template or "")
    rendered = re.sub(r"[ \t]+", " ", rendered)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered)
    return rendered.strip()


def build_bot_message_context(
    *,
    tenant: Any = None,
    config: Any = None,
    client: Any = None,
    service: Any = None,
    appointment: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    extra = dict(extra or {})
    service_price = _attr(service, "price")
    service_duration = _attr(service, "duration_minutes")
    appointment_date = _attr(appointment, "appointment_date")
    appointment_time = _attr(appointment, "start_time")

    return {
        "business_name": extra.get("business_name", _attr(tenant, "name")),
        "client_name": extra.get("client_name", _attr(client, "full_name")),
        "service_name": extra.get("service_name", _attr(service, "name")),
        "date": extra.get("date", appointment_date),
        "time": extra.get("time", appointment_time),
        "phone": extra.get("phone", _attr(client, "phone")),
        "price": extra.get("price", service_price),
        "duration": extra.get("duration", service_duration),
        "bot_name": extra.get("bot_name", _attr(config, "bot_name") or _attr(config, "bot_username")),
        "business_phone": extra.get("business_phone", _attr(tenant, "phone")),
        "business_address": extra.get("business_address", _attr(tenant, "address")),
        "appointment_status": extra.get("appointment_status", _attr(appointment, "status")),
    }
