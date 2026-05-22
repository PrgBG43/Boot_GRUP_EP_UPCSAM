"""Disponibilidad de agenda por negocio.

La configuración vive en Tenant para que cada negocio la administre desde el
panel: horario semanal, pausas, bloqueos y anticipación de reservas.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.plan_usage_service import can_create_appointment

FREE_MAX_BOOKING_DAYS = 7
PREMIUM_DEFAULT_MAX_BOOKING_DAYS = 30
DEFAULT_WEEKLY_SCHEDULE = {
    "0": {"active": True, "open": "08:00", "close": "18:00", "break_start": "", "break_end": ""},
    "1": {"active": True, "open": "08:00", "close": "18:00", "break_start": "", "break_end": ""},
    "2": {"active": True, "open": "08:00", "close": "18:00", "break_start": "", "break_end": ""},
    "3": {"active": True, "open": "08:00", "close": "18:00", "break_start": "", "break_end": ""},
    "4": {"active": True, "open": "08:00", "close": "18:00", "break_start": "", "break_end": ""},
    "5": {"active": True, "open": "08:00", "close": "16:00", "break_start": "", "break_end": ""},
    "6": {"active": False, "open": "08:00", "close": "16:00", "break_start": "", "break_end": ""},
}


def _parse_time(value: Optional[str], fallback: Optional[time] = None) -> Optional[time]:
    if not value:
        return fallback
    try:
        return datetime.strptime(value[:5], "%H:%M").time()
    except (TypeError, ValueError):
        return fallback


def _time_to_label(value: str) -> str:
    parsed = _parse_time(value)
    if not parsed:
        return value
    suffix = "a. m." if parsed.hour < 12 else "p. m."
    hour = parsed.hour % 12 or 12
    return f"{hour}:{parsed.minute:02d} {suffix}"


def get_tenant_schedule(tenant: Tenant) -> dict[str, Any]:
    schedule = tenant.weekly_schedule or {}
    merged = {}
    for key, defaults in DEFAULT_WEEKLY_SCHEDULE.items():
        item = {**defaults, **(schedule.get(key) or {})}
        if key in {"0", "1", "2", "3", "4"}:
            item["open"] = item.get("open") or tenant.opening_time or defaults["open"]
            item["close"] = item.get("close") or tenant.closing_time or defaults["close"]
        merged[key] = item
    return merged


def get_max_booking_days(tenant: Tenant) -> int:
    plan_name = (tenant.plan.name if tenant and tenant.plan else "free").lower()
    configured = tenant.max_booking_days or PREMIUM_DEFAULT_MAX_BOOKING_DAYS
    if plan_name == "free":
        return min(configured, FREE_MAX_BOOKING_DAYS)
    return max(configured, 1)


def build_slots(open_time: time, close_time: time, duration_minutes: int, step_minutes: int, target_date: date) -> list[tuple[time, time]]:
    slots: list[tuple[time, time]] = []
    current = datetime.combine(target_date, open_time)
    closing = datetime.combine(target_date, close_time)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=max(step_minutes, 5))

    while current + duration <= closing:
        slots.append((current.time(), (current + duration).time()))
        current += step
    return slots


def _overlaps(start: time, end: time, blocked_start: time, blocked_end: time) -> bool:
    return start < blocked_end and end > blocked_start


def exclude_existing_appointments(slots: Iterable[tuple[time, time]], appointments: Iterable[Appointment]) -> list[tuple[time, time]]:
    booked = [(item.start_time, item.end_time) for item in appointments]
    return [
        (start, end)
        for start, end in slots
        if not any(_overlaps(start, end, booked_start, booked_end) for booked_start, booked_end in booked)
    ]


def exclude_blocked_ranges(slots: Iterable[tuple[time, time]], blocked_ranges: Iterable[dict[str, Any]]) -> list[tuple[time, time]]:
    parsed_ranges = []
    for item in blocked_ranges:
        start = _parse_time(item.get("start"))
        end = _parse_time(item.get("end"))
        if start and end and start < end:
            parsed_ranges.append((start, end))
    return [
        (start, end)
        for start, end in slots
        if not any(_overlaps(start, end, blocked_start, blocked_end) for blocked_start, blocked_end in parsed_ranges)
    ]


def _blocked_ranges_for_date(tenant: Tenant, target_date: date) -> list[dict[str, Any]]:
    return [
        item
        for item in (tenant.blocked_time_ranges or [])
        if item.get("date") == target_date.isoformat()
    ]


def _is_blocked_date(tenant: Tenant, target_date: date) -> bool:
    return any(item.get("date") == target_date.isoformat() for item in (tenant.blocked_dates or []))


def _date_is_in_booking_window(tenant: Tenant, target_date: date, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    today = now.date()
    if target_date < today:
        return False
    max_days = get_max_booking_days(tenant)
    return target_date <= today + timedelta(days=max_days)


def _minimum_notice_allows(target_date: date, slot_start: time, tenant: Tenant, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    min_notice = timedelta(minutes=tenant.min_booking_notice_minutes or 0)
    return datetime.combine(target_date, slot_start) >= now + min_notice


def get_day_config(tenant: Tenant, target_date: date) -> Optional[dict[str, Any]]:
    schedule = get_tenant_schedule(tenant)
    config = schedule.get(str(target_date.weekday()))
    if not config or not config.get("active"):
        return None
    return config


def get_available_slots(
    db: Session,
    tenant_id: int,
    service_id: int,
    target_date: date,
    *,
    include_plan_limit: bool = True,
) -> list[str]:
    """Retorna horarios disponibles en formato HH:MM."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
    if not tenant or tenant.status == "archived":
        return []
    if include_plan_limit and not can_create_appointment(db, tenant_id):
        return []

    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant_id, Service.is_active == True)
        .first()
    )
    if not service or not _date_is_in_booking_window(tenant, target_date) or _is_blocked_date(tenant, target_date):
        return []

    day_config = get_day_config(tenant, target_date)
    if not day_config:
        return []

    opening = _parse_time(day_config.get("open"), _parse_time(tenant.opening_time, time(8, 0)))
    closing = _parse_time(day_config.get("close"), _parse_time(tenant.closing_time, time(18, 0)))
    if not opening or not closing or opening >= closing:
        return []

    step_minutes = tenant.base_slot_minutes or 30
    slots = build_slots(opening, closing, service.duration_minutes, step_minutes, target_date)

    break_start = _parse_time(day_config.get("break_start"))
    break_end = _parse_time(day_config.get("break_end"))
    if break_start and break_end and break_start < break_end:
        slots = exclude_blocked_ranges(slots, [{"start": break_start.strftime("%H:%M"), "end": break_end.strftime("%H:%M")}])

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.appointment_date == target_date,
            Appointment.status.notin_(["cancelled", "no_show"]),
        )
        .all()
    )
    slots = exclude_existing_appointments(slots, existing)
    slots = exclude_blocked_ranges(slots, _blocked_ranges_for_date(tenant, target_date))
    slots = [(start, end) for start, end in slots if _minimum_notice_allows(target_date, start, tenant)]
    return [start.strftime("%H:%M") for start, _ in slots]


def get_available_dates(db: Session, tenant_id: int, service_id: int) -> list[dict[str, str]]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
    if not tenant or tenant.status == "archived" or not can_create_appointment(db, tenant_id):
        return []

    today = datetime.now().date()
    max_days = get_max_booking_days(tenant)
    available = []
    for offset in range(max_days + 1):
        target_date = today + timedelta(days=offset)
        slots = get_available_slots(db, tenant_id, service_id, target_date)
        if slots:
            available.append({"date": target_date.isoformat(), "label": format_date_label(target_date)})
        if len(available) >= 10:
            break
    return available


def is_slot_available(db: Session, tenant_id: int, service_id: int, target_date: date, start_time: time) -> bool:
    return start_time.strftime("%H:%M") in get_available_slots(
        db,
        tenant_id,
        service_id,
        target_date,
        include_plan_limit=False,
    )


def format_date_label(target_date: date) -> str:
    today = datetime.now().date()
    if target_date == today:
        return "Hoy"
    if target_date == today + timedelta(days=1):
        return "Mañana"
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    return f"{days[target_date.weekday()]} {target_date.day}"


def format_time_label(value: str) -> str:
    return _time_to_label(value)
