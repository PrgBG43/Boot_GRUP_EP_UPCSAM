"""Endpoints analíticos para superadmin, negocios y staff."""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user, require_staff_or_above, require_superadmin
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.plan import Plan
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.plan_usage_service import get_plan_usage_summary

router = APIRouter()


def _add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def _date_range(date_from: Optional[date], date_to: Optional[date], *, months_back: int = 5) -> tuple[date, date]:
    today = date.today()
    start = date_from or _add_months(today.replace(day=1), -months_back)
    end = date_to or today
    if start > end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rango de fechas no es válido.")
    return start, end


def _month_key(value: date | datetime) -> str:
    raw = value.date() if isinstance(value, datetime) else value
    return f"{raw.year:04d}-{raw.month:02d}"


def _day_key(value: date | datetime) -> str:
    raw = value.date() if isinstance(value, datetime) else value
    return raw.isoformat()


def _month_buckets(start: date, end: date) -> list[str]:
    current = start.replace(day=1)
    last = end.replace(day=1)
    buckets = []
    while current <= last:
        buckets.append(_month_key(current))
        current = _add_months(current, 1)
    return buckets


def _day_buckets(start: date, end: date, *, limit: int = 60) -> list[str]:
    days = (end - start).days + 1
    if days > limit:
        start = end - timedelta(days=limit - 1)
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def _money(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _tenant_query(db: Session, *, tenant_id: Optional[int], plan: Optional[str], city: Optional[str], status_filter: Optional[str]):
    query = db.query(Tenant).options(joinedload(Tenant.plan))
    if tenant_id:
        query = query.filter(Tenant.id == tenant_id)
    if plan:
        query = query.join(Plan, Tenant.plan_id == Plan.id).filter(Plan.name == plan)
    if city:
        term = f"%{city.strip()}%"
        query = query.filter(or_(Tenant.city.ilike(term), Tenant.slug.ilike(term), Tenant.name.ilike(term)))
    if status_filter in {"active", "activo"}:
        query = query.filter(Tenant.is_active == True, or_(Tenant.status != "archived", Tenant.status.is_(None)))
    elif status_filter in {"inactive", "inactivo"}:
        query = query.filter(Tenant.is_active == False, or_(Tenant.status != "archived", Tenant.status.is_(None)))
    elif status_filter in {"archived", "archivado"}:
        query = query.filter(Tenant.status == "archived")
    elif status_filter not in {None, "", "all", "todos"}:
        query = query.filter(Tenant.status == status_filter)
    return query


def _filter_by_tenants(query, model, tenant_ids: list[int]):
    if not tenant_ids:
        return query.filter(False)
    return query.filter(model.tenant_id.in_(tenant_ids))


def _appointments_in_range(db: Session, tenant_ids: list[int], start: date, end: date, appointment_status: Optional[str] = None):
    query = (
        db.query(Appointment)
        .options(joinedload(Appointment.service), joinedload(Appointment.tenant))
        .filter(Appointment.appointment_date >= start, Appointment.appointment_date <= end)
    )
    query = _filter_by_tenants(query, Appointment, tenant_ids)
    if appointment_status:
        query = query.filter(Appointment.status == appointment_status)
    return query.all()


def _clients_in_range(db: Session, tenant_ids: list[int], start: date, end: date):
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    query = db.query(Client).filter(Client.created_at >= start_dt, Client.created_at <= end_dt)
    return _filter_by_tenants(query, Client, tenant_ids).all()


def _conversations_in_range(db: Session, tenant_ids: list[int], start: date, end: date):
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    query = db.query(Conversation).filter(Conversation.last_interaction_at >= start_dt, Conversation.last_interaction_at <= end_dt)
    return _filter_by_tenants(query, Conversation, tenant_ids).all()


def _chart_from_counter(counter: Counter, label_key: str, value_key: str, ordered_keys: Optional[list[str]] = None):
    keys = ordered_keys if ordered_keys is not None else list(counter.keys())
    return [{label_key: key, value_key: int(counter.get(key, 0))} for key in keys]


@router.get("/superadmin", summary="Dashboard global (solo superadmin)")
def superadmin_dashboard(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    tenant_id: Optional[int] = Query(None),
    plan: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    start, end = _date_range(date_from, date_to, months_back=5)
    tenants = _tenant_query(db, tenant_id=tenant_id, plan=plan, city=city, status_filter=status_filter).all()
    tenant_ids = [tenant.id for tenant in tenants]
    appointments = _appointments_in_range(db, tenant_ids, start, end)
    clients = _clients_in_range(db, tenant_ids, start, end)
    conversations = _conversations_in_range(db, tenant_ids, start, end)

    plan_counts = Counter((tenant.plan.name if tenant.plan else "sin_plan") for tenant in tenants)
    plan_labels = {tenant.plan.name: tenant.plan.display_name for tenant in tenants if tenant.plan}
    tenant_by_id = {tenant.id: tenant for tenant in tenants}

    status_counts = Counter(appt.status for appt in appointments)
    monthly_appts = Counter(_month_key(appt.appointment_date) for appt in appointments)
    monthly_clients = Counter(_month_key(client.created_at) for client in clients if client.created_at)
    monthly_conversations = Counter(_month_key(conv.last_interaction_at) for conv in conversations if conv.last_interaction_at)
    city_appts = Counter((appt.tenant.city if appt.tenant and appt.tenant.city else "Sin ciudad") for appt in appointments)
    business_growth = Counter(_month_key(tenant.created_at) for tenant in tenants if tenant.created_at)
    top_businesses_counter = Counter()
    appts_by_plan = Counter()

    for appt in appointments:
        tenant = tenant_by_id.get(appt.tenant_id)
        if tenant:
            top_businesses_counter[tenant.name] += 1
            appts_by_plan[tenant.plan.name if tenant.plan else "sin_plan"] += 1

    usage_rows = []
    for tenant in tenants:
        usage = get_plan_usage_summary(db, tenant.id)
        if usage["near_limit"] or usage["limit_reached"] or usage["plan"] == "free":
            usage_rows.append(usage)

    top_plan = plan_counts.most_common(1)[0][0] if plan_counts else None
    top_business = top_businesses_counter.most_common(1)[0] if top_businesses_counter else None
    premium_volume = appts_by_plan.get("premium", 0)
    free_volume = appts_by_plan.get("free", 0)
    near_limit = [item for item in usage_rows if item["near_limit"] and not item["limit_reached"]]
    limit_reached = [item for item in usage_rows if item["limit_reached"]]

    insights = []
    if top_plan:
        insights.append(f"El plan con mayor presencia es {plan_labels.get(top_plan, top_plan)}.")
    if premium_volume or free_volume:
        comparison = "mayor" if premium_volume >= free_volume else "menor"
        insights.append(f"Los negocios Premium generan un volumen {comparison} de citas frente al plan Gratuito en el rango seleccionado.")
    if near_limit:
        insights.append(f"Hay {len(near_limit)} negocio(s) cerca del límite gratuito.")
    if limit_reached:
        insights.append(f"{len(limit_reached)} negocio(s) alcanzaron el límite gratuito.")
    if top_business:
        insights.append(f"El negocio con mayor actividad es {top_business[0]} con {top_business[1]} citas.")
    if not insights:
        insights.append("Todavía no hay suficiente actividad para generar análisis del periodo.")

    months = _month_buckets(start, end)
    active_tenants = [tenant for tenant in tenants if tenant.is_active and tenant.status != "archived"]
    archived_tenants = [tenant for tenant in tenants if tenant.status == "archived"]
    inactive_tenants = [tenant for tenant in tenants if not tenant.is_active and tenant.status != "archived"]

    summary = {
        "total_businesses": len(tenants),
        "active_businesses": len(active_tenants),
        "inactive_businesses": len(inactive_tenants),
        "archived_businesses": len(archived_tenants),
        "free_businesses": plan_counts.get("free", 0),
        "premium_businesses": plan_counts.get("premium", 0),
        "monthly_appointments": len([a for a in appointments if a.appointment_date >= date.today().replace(day=1)]),
        "total_clients": db.query(func.count(Client.id)).filter(Client.tenant_id.in_(tenant_ids)).scalar() if tenant_ids else 0,
        "clients_in_range": len(clients),
        "total_conversations": db.query(func.count(Conversation.id)).filter(Conversation.tenant_id.in_(tenant_ids)).scalar() if tenant_ids else 0,
        "conversations_in_range": len(conversations),
        "near_limit_businesses": len(near_limit),
        "limit_reached_businesses": len(limit_reached),
        "appointments_in_range": len(appointments),
    }

    charts = {
        "appointments_by_month": _chart_from_counter(monthly_appts, "month", "appointments", months),
        "appointments_by_status": _chart_from_counter(status_counts, "status", "count"),
        "businesses_by_plan": [
            {"plan": key, "label": plan_labels.get(key, "Sin plan" if key == "sin_plan" else key), "count": value}
            for key, value in plan_counts.items()
        ],
        "top_businesses": [
            {"name": name, "appointments": count}
            for name, count in top_businesses_counter.most_common(8)
        ],
        "clients_by_month": _chart_from_counter(monthly_clients, "month", "clients", months),
        "conversations_by_month": _chart_from_counter(monthly_conversations, "month", "conversations", months),
        "appointments_by_city": [
            {"city": name, "appointments": count}
            for name, count in city_appts.most_common(8)
        ],
        "free_plan_usage": usage_rows[:12],
        "business_growth": _chart_from_counter(business_growth, "month", "businesses", months),
    }

    return {
        "summary": summary,
        "charts": charts,
        "insights": insights,
        "filters": {"date_from": start.isoformat(), "date_to": end.isoformat(), "tenant_id": tenant_id, "plan": plan, "city": city, "status": status_filter},
        # Compatibilidad con el dashboard anterior.
        "total_tenants": summary["total_businesses"],
        "active_tenants": summary["active_businesses"],
        "inactive_tenants": summary["inactive_businesses"],
        "archived_tenants": summary["archived_businesses"],
        "free_tenants": summary["free_businesses"],
        "premium_tenants": summary["premium_businesses"],
        "total_clients": summary["total_clients"],
        "appointments_this_month": summary["monthly_appointments"],
        "plan_distribution": charts["businesses_by_plan"],
        "top_tenants_month": charts["top_businesses"],
        "tenants_near_limit": near_limit,
        "tenants_limit_reached": limit_reached,
    }


@router.get("/tenant", summary="Dashboard del negocio")
def tenant_dashboard(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    tenant_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if current_user.primary_role == "superadmin":
        if tenant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecciona un negocio.")
        tid = tenant_id
    else:
        tid = current_user.tenant_id
    if not tid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario sin negocio asignado.")

    tenant = db.query(Tenant).options(joinedload(Tenant.plan)).filter(Tenant.id == tid).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negocio no encontrado.")

    start, end = _date_range(date_from, date_to, months_back=0)
    if date_from is None and date_to is None:
        start = date.today().replace(day=1)
        end = date.today()

    appointments = _appointments_in_range(db, [tid], start, end, status_filter)
    conversations = _conversations_in_range(db, [tid], start, end)
    new_clients = _clients_in_range(db, [tid], start, end)
    all_clients = db.query(func.count(Client.id)).filter(Client.tenant_id == tid).scalar() or 0
    active_services = db.query(func.count(Service.id)).filter(Service.tenant_id == tid, Service.is_active == True).scalar() or 0
    total_services = db.query(func.count(Service.id)).filter(Service.tenant_id == tid).scalar() or 0

    status_counts = Counter(appt.status for appt in appointments)
    top_services = Counter(appt.service.name if appt.service else "Sin servicio" for appt in appointments)
    demand_hours = Counter(appt.start_time.strftime("%H:00") for appt in appointments if appt.start_time)
    appts_by_day = Counter(_day_key(appt.appointment_date) for appt in appointments)
    conversations_by_day = Counter(_day_key(conv.last_interaction_at) for conv in conversations if conv.last_interaction_at)
    clients_by_month = Counter(_month_key(client.created_at) for client in new_clients if client.created_at)
    revenue_by_service = defaultdict(float)
    estimated_income = 0.0
    for appt in appointments:
        if appt.status in {"confirmed", "completed"} and appt.service:
            value = _money(appt.service.price)
            estimated_income += value
            revenue_by_service[appt.service.name] += value

    today = date.today()
    appointments_today = db.query(func.count(Appointment.id)).filter(Appointment.tenant_id == tid, Appointment.appointment_date == today).scalar() or 0
    plan_usage = get_plan_usage_summary(db, tid)
    monthly_limit = plan_usage.get("monthly_limit")
    used_this_month = plan_usage.get("used_this_month", 0)
    remaining = None if monthly_limit is None else max(monthly_limit - used_this_month, 0)
    top_service = top_services.most_common(1)[0] if top_services else None
    top_hour = demand_hours.most_common(1)[0] if demand_hours else None

    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date >= today,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(8)
        .all()
    )

    insights = []
    if top_service:
        insights.append(f"Tu servicio más solicitado es {top_service[0]} con {top_service[1]} citas.")
    if top_hour:
        insights.append(f"Tu horario con mayor demanda es {top_hour[0]}.")
    if monthly_limit:
        insights.append(f"Has usado {used_this_month} de {monthly_limit} citas disponibles este mes.")
        insights.append(f"Te quedan {remaining} citas disponibles en tu plan Gratuito.")
        if plan_usage.get("near_limit"):
            insights.append("Estás cerca de alcanzar el límite mensual.")
    if not insights:
        insights.append("Aún no hay suficiente actividad para generar análisis del negocio.")

    days = _day_buckets(start, end)
    months = _month_buckets(start, end)
    summary = {
        "appointments_in_range": len(appointments),
        "appointments_today": appointments_today,
        "pending_appointments": status_counts.get("pending", 0),
        "confirmed_appointments": status_counts.get("confirmed", 0),
        "completed_appointments": status_counts.get("completed", 0),
        "cancelled_appointments": status_counts.get("cancelled", 0),
        "clients_registered": all_clients,
        "new_clients_in_range": len(new_clients),
        "conversations_received": len(conversations),
        "plan_used": used_this_month,
        "plan_limit": monthly_limit,
        "plan_remaining": remaining,
        "top_service": top_service[0] if top_service else None,
        "estimated_income": estimated_income,
        "active_services": active_services,
        "total_services": total_services,
    }

    charts = {
        "appointments_by_day": _chart_from_counter(appts_by_day, "date", "appointments", days),
        "appointments_by_status": _chart_from_counter(status_counts, "status", "count"),
        "top_services": [{"name": name, "appointments": count} for name, count in top_services.most_common(8)],
        "new_clients_by_month": _chart_from_counter(clients_by_month, "month", "clients", months),
        "demand_by_hour": [{"hour": hour, "appointments": count} for hour, count in sorted(demand_hours.items())],
        "conversations_by_day": _chart_from_counter(conversations_by_day, "date", "conversations", days),
        "revenue_by_service": [{"name": name, "revenue": round(value, 2)} for name, value in sorted(revenue_by_service.items(), key=lambda item: item[1], reverse=True)],
        "plan_usage": [
            {"name": "Usadas", "value": used_this_month},
            {"name": "Restantes", "value": remaining or 0},
        ] if monthly_limit else [{"name": "Ilimitado", "value": used_this_month}],
    }

    return {
        "summary": summary,
        "charts": charts,
        "insights": insights,
        "filters": {"date_from": start.isoformat(), "date_to": end.isoformat(), "tenant_id": tid, "status": status_filter},
        "plan_usage": plan_usage,
        "tenant": {"id": tenant.id, "name": tenant.name, "plan": tenant.plan.name if tenant.plan else None},
        "upcoming_appointments": [
            {
                "id": appt.id,
                "date": str(appt.appointment_date),
                "start_time": str(appt.start_time),
                "service_id": appt.service_id,
                "client_id": appt.client_id,
                "status": appt.status,
            }
            for appt in upcoming
        ],
        # Compatibilidad con el dashboard anterior.
        "total_services": total_services,
        "active_services": active_services,
        "total_clients": all_clients,
        "appointments_today": appointments_today,
        "appointments_month": len(appointments),
        "completed_month": summary["completed_appointments"],
        "cancelled_month": summary["cancelled_appointments"],
        "pending_month": summary["pending_appointments"] + summary["confirmed_appointments"],
        "conversations_month": len(conversations),
        "estimated_income": estimated_income,
        "top_service": {"name": top_service[0], "count": top_service[1]} if top_service else None,
        "daily_chart": charts["appointments_by_day"],
    }


@router.get("/staff", summary="Dashboard limitado del staff")
def staff_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("staff", "tenant_admin", "superadmin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    if current_user.primary_role == "superadmin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecciona un negocio para ver agenda de staff.")
    tid = current_user.tenant_id
    today = date.today()
    month_start = today.replace(day=1)

    today_appointments = (
        db.query(Appointment)
        .filter(Appointment.tenant_id == tid, Appointment.appointment_date == today)
        .order_by(Appointment.start_time)
        .all()
    )
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tid,
            Appointment.appointment_date >= today,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(10)
        .all()
    )
    month_appointments = (
        db.query(Appointment)
        .filter(Appointment.tenant_id == tid, Appointment.appointment_date >= month_start, Appointment.appointment_date <= today)
        .all()
    )
    status_counts = Counter(appt.status for appt in month_appointments)
    client_ids = {appt.client_id for appt in month_appointments if appt.status == "completed"}

    summary = {
        "appointments_today": len(today_appointments),
        "upcoming_appointments": len(upcoming),
        "completed_appointments": status_counts.get("completed", 0),
        "pending_appointments": status_counts.get("pending", 0) + status_counts.get("confirmed", 0),
        "clients_served": len(client_ids),
    }
    return {
        "summary": summary,
        "charts": {"appointments_by_status": _chart_from_counter(status_counts, "status", "count")},
        "insights": [
            f"Tienes {summary['appointments_today']} cita(s) para hoy.",
            f"Hay {summary['pending_appointments']} cita(s) pendientes o confirmadas este mes.",
        ],
        "appointments_today": summary["appointments_today"],
        "upcoming_count": summary["upcoming_appointments"],
        "completed_this_month": summary["completed_appointments"],
        "today_appointments": [
            {
                "id": appt.id,
                "date": str(appt.appointment_date),
                "start_time": str(appt.start_time),
                "service_id": appt.service_id,
                "client_id": appt.client_id,
                "status": appt.status,
                "notes": appt.notes,
            }
            for appt in today_appointments
        ],
        "upcoming_appointments": [
            {
                "id": appt.id,
                "date": str(appt.appointment_date),
                "start_time": str(appt.start_time),
                "service_id": appt.service_id,
                "client_id": appt.client_id,
                "status": appt.status,
            }
            for appt in upcoming
        ],
    }
