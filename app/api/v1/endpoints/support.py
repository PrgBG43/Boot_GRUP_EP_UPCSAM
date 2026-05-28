from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.plan import Plan
from app.models.support import SupportTicket, SupportTicketMessage
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.support import (
    SupportTicketCreate,
    SupportTicketMessageCreate,
    SupportTicketMessageResponse,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from app.services.pagination import paginate_query

router = APIRouter()

SUPPORT_ROLES = {"superadmin"}
TENANT_ADMIN_ROLES = {"tenant_admin"}
TENANT_SUPPORT_ROLES = {"tenant_admin", "staff", "customer"}
ACTIVE_STATUSES = {"open", "in_progress", "waiting_user"}
HIDDEN_STATUSES = {"archived"}
ACCESS_DENIED_MESSAGE = "No tienes permiso para acceder a este ticket."
HISTORY_DELETE_MESSAGE = (
    "Este ticket tiene mensajes o trazabilidad asociada. "
    "Puedes archivarlo, pero no eliminarlo definitivamente."
)


def _serialize(ticket: SupportTicket, *, include_messages: bool = False, user: Optional[User] = None) -> dict:
    messages = ticket.messages if include_messages else []
    if include_messages and user and user.primary_role not in SUPPORT_ROLES:
        messages = [
            message
            for message in messages
            if not message.is_internal_note or message.sender_user_id == user.id
        ]
    return {
        "id": ticket.id,
        "tenant_id": ticket.tenant_id,
        "tenant_name": ticket.tenant_name,
        "tenant_plan": ticket.tenant_plan,
        "tenant_plan_label": ticket.tenant_plan_label,
        "is_premium": ticket.is_premium,
        "created_by_user_id": ticket.created_by_user_id,
        "assigned_to_user_id": ticket.assigned_to_user_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "messages": [_serialize_message(message) for message in messages] if include_messages else [],
    }


def _serialize_message(message: SupportTicketMessage) -> dict:
    return {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "sender_user_id": message.sender_user_id,
        "sender_name": message.sender_name,
        "sender_role": message.sender_role,
        "message": message.message,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "is_internal_note": bool(message.is_internal_note),
    }


def _assert_support_access(user: User) -> None:
    if user.primary_role in SUPPORT_ROLES:
        return
    if user.primary_role in TENANT_SUPPORT_ROLES and user.tenant_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_MESSAGE)


def _can_access_ticket(user: User, ticket: SupportTicket) -> bool:
    if user.primary_role in SUPPORT_ROLES:
        return True
    if ticket.created_by_user_id == user.id:
        return True
    if ticket.assigned_to_user_id == user.id:
        return True
    if (
        user.primary_role in TENANT_ADMIN_ROLES
        and user.tenant_id is not None
        and user.tenant_id == ticket.tenant_id
    ):
        return True
    return False


def _assert_ticket_access(user: User, ticket: SupportTicket) -> None:
    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_MESSAGE)


def _assert_ticket_owner_or_support(user: User, ticket: SupportTicket) -> None:
    if user.primary_role in SUPPORT_ROLES:
        return
    if ticket.created_by_user_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_MESSAGE)


def _apply_ticket_visibility(query, user: User):
    if user.primary_role in SUPPORT_ROLES:
        return query

    conditions = [
        SupportTicket.created_by_user_id == user.id,
        SupportTicket.assigned_to_user_id == user.id,
    ]
    if user.primary_role in TENANT_ADMIN_ROLES and user.tenant_id is not None:
        conditions.append(SupportTicket.tenant_id == user.tenant_id)
    return query.filter(or_(*conditions))


def _tenant_for_ticket(db: Session, user: User, tenant_id: Optional[int]) -> Tenant:
    if user.primary_role in SUPPORT_ROLES:
        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecciona un negocio.")
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    else:
        if not user.tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario sin negocio asignado.")
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negocio no encontrado.")
    return tenant


def _premium_priority(tenant: Tenant, priority: str) -> str:
    if tenant.plan and tenant.plan.name == "premium" and priority in {"low", "normal"}:
        return "high"
    return priority


def _load_ticket(db: Session, ticket_id: int, *, include_messages: bool = False) -> SupportTicket:
    options = [joinedload(SupportTicket.tenant).joinedload(Tenant.plan)]
    if include_messages:
        options.append(joinedload(SupportTicket.messages).joinedload(SupportTicketMessage.sender))
    ticket = db.query(SupportTicket).options(*options).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    return ticket


def _ticket_has_important_history(ticket: SupportTicket) -> bool:
    messages = list(ticket.messages or [])
    if any(message.is_internal_note for message in messages):
        return True
    if any(message.sender_user_id != ticket.created_by_user_id for message in messages):
        return True
    if len(messages) > 1:
        return True
    if ticket.assigned_to_user_id is not None:
        return True
    return (ticket.status or "").lower() not in {"open", "archived"}


@router.get("/tickets")
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)

    query = (
        db.query(SupportTicket)
        .options(joinedload(SupportTicket.tenant).joinedload(Tenant.plan))
        .outerjoin(Tenant, Tenant.id == SupportTicket.tenant_id)
        .outerjoin(Plan, Plan.id == Tenant.plan_id)
    )
    query = _apply_ticket_visibility(query, current_user)

    if current_user.primary_role in SUPPORT_ROLES:
        if tenant_id:
            query = query.filter(SupportTicket.tenant_id == tenant_id)
        if plan:
            query = query.filter(Plan.name == plan)

    if status_filter and status_filter not in {"all", "todos", "todo"}:
        query = query.filter(SupportTicket.status == status_filter)
    elif not status_filter:
        query = query.filter(SupportTicket.status.notin_(HIDDEN_STATUSES))
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(SupportTicket.subject.ilike(term), SupportTicket.description.ilike(term), Tenant.name.ilike(term)))

    priority_rank = case(
        (SupportTicket.priority == "urgent", 0),
        (SupportTicket.priority == "high", 1),
        (Plan.name == "premium", 2),
        else_=3,
    )
    active_rank = case((SupportTicket.status.in_(ACTIVE_STATUSES), 0), else_=1)
    query = query.order_by(active_rank.asc(), priority_rank.asc(), SupportTicket.updated_at.asc())

    page_data = paginate_query(query, page, page_size)
    return {**page_data, "items": [_serialize(item, user=current_user) for item in page_data["items"]]}


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    tenant = _tenant_for_ticket(db, current_user, payload.tenant_id)
    priority = _premium_priority(tenant, payload.priority)
    ticket = SupportTicket(
        tenant_id=tenant.id,
        created_by_user_id=current_user.id,
        subject=payload.subject,
        description=payload.description,
        category=payload.category or "general",
        priority=priority,
        status="open",
    )
    db.add(ticket)
    db.flush()
    db.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            message=payload.description,
            is_internal_note=False,
        )
    )
    db.commit()
    created = (
        db.query(SupportTicket)
        .options(
            joinedload(SupportTicket.tenant).joinedload(Tenant.plan),
            joinedload(SupportTicket.messages).joinedload(SupportTicketMessage.sender),
        )
        .filter(SupportTicket.id == ticket.id)
        .first()
    )
    return _serialize(created or ticket, include_messages=True, user=current_user)


@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id, include_messages=True)
    _assert_ticket_access(current_user, ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.put("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_ticket(
    ticket_id: int,
    payload: SupportTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_access(current_user, ticket)

    data = payload.model_dump(exclude_unset=True)
    if current_user.primary_role not in SUPPORT_ROLES:
        _assert_ticket_owner_or_support(current_user, ticket)
        data.pop("assigned_to_user_id", None)
        data.pop("status", None)
        data.pop("priority", None)
    if "priority" in data and data["priority"]:
        data["priority"] = _premium_priority(ticket.tenant, data["priority"])
    if "assigned_to_user_id" in data and data["assigned_to_user_id"] is not None:
        assignee = db.query(User).filter(User.id == data["assigned_to_user_id"], User.is_active == True).first()
        if not assignee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario asignado no encontrado.")
        if assignee.primary_role not in SUPPORT_ROLES and assignee.tenant_id != ticket.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario asignado no pertenece al negocio del ticket.",
            )
    if data.get("status") == "closed" and ticket.status != "closed":
        data["closed_at"] = datetime.now(timezone.utc)
    elif data.get("status") and data["status"] != "closed":
        data["closed_at"] = None

    for key, value in data.items():
        setattr(ticket, key, value)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.post("/tickets/{ticket_id}/messages", response_model=SupportTicketMessageResponse, status_code=status.HTTP_201_CREATED)
def add_ticket_message(
    ticket_id: int,
    payload: SupportTicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_access(current_user, ticket)
    if payload.is_internal_note and current_user.primary_role not in SUPPORT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_MESSAGE)

    message = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_user_id=current_user.id,
        message=payload.message,
        is_internal_note=payload.is_internal_note,
    )
    if current_user.primary_role in SUPPORT_ROLES and ticket.status == "open":
        ticket.status = "in_progress"
    elif current_user.primary_role in TENANT_SUPPORT_ROLES and ticket.status == "waiting_user":
        ticket.status = "in_progress"
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    created = (
        db.query(SupportTicketMessage)
        .options(joinedload(SupportTicketMessage.sender))
        .filter(SupportTicketMessage.id == message.id)
        .first()
    )
    return _serialize_message(created or message)


@router.post("/tickets/{ticket_id}/close", response_model=SupportTicketResponse)
def close_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_owner_or_support(current_user, ticket)
    ticket.status = "closed"
    ticket.closed_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.post("/tickets/{ticket_id}/reopen", response_model=SupportTicketResponse)
def reopen_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_owner_or_support(current_user, ticket)
    ticket.status = "open"
    ticket.closed_at = None
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.post("/tickets/{ticket_id}/archive", response_model=SupportTicketResponse)
def archive_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_owner_or_support(current_user, ticket)
    ticket.status = "archived"
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.post("/tickets/{ticket_id}/restore", response_model=SupportTicketResponse)
def restore_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id)
    _assert_ticket_owner_or_support(current_user, ticket)
    if ticket.status == "archived":
        ticket.status = "open"
        ticket.closed_at = None
        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
    return _serialize(ticket, include_messages=True, user=current_user)


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_support_access(current_user)
    ticket = _load_ticket(db, ticket_id, include_messages=True)
    _assert_ticket_owner_or_support(current_user, ticket)
    if _ticket_has_important_history(ticket):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=HISTORY_DELETE_MESSAGE)
    db.delete(ticket)
    db.commit()
