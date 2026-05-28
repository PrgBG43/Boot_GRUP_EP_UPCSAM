from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_staff_or_above, require_tenant_admin_or_above
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.user import User
from app.repositories import client_repository
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.services.pagination import paginate_query

router = APIRouter()

CLIENT_HISTORY_MESSAGE = (
    "Este cliente tiene historial asociado. "
    "Puedes archivarlo, pero no eliminarlo definitivamente."
)


def _client_has_history(db: Session, client_id: int) -> bool:
    return bool(
        db.query(Appointment.id).filter(Appointment.client_id == client_id).first()
        or db.query(Conversation.id).filter(Conversation.client_id == client_id).first()
    )


@router.get("/")
def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if skip:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size
    effective_tenant = tenant_id if current_user.primary_role == "superadmin" else current_user.tenant_id
    query = db.query(Client)
    if effective_tenant is not None:
        query = query.filter(Client.tenant_id == effective_tenant)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(Client.full_name.ilike(term), Client.username.ilike(term), Client.phone.ilike(term))
        )
    if status_filter in {"archived", "archivado"}:
        query = query.filter(Client.status == "archived")
    elif status_filter not in {"all", "todos", "todo"}:
        query = query.filter(or_(Client.status != "archived", Client.status.is_(None)))
    sortable = {"created_at": Client.created_at, "full_name": Client.full_name, "id": Client.id}
    column = sortable.get(sort_by, Client.created_at)
    query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    page_data = paginate_query(query, page, page_size)
    return {
        **page_data,
        "items": [ClientResponse.model_validate(item).model_dump(mode="json") for item in page_data["items"]],
    }


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    if current_user.primary_role == "superadmin":
        if not client.tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecciona un negocio.")
    else:
        client = client.model_copy(update={"tenant_id": current_user.tenant_id})
    if current_user.primary_role != "superadmin" and client.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return client_repository.create_client(db, client)


@router.get("/telegram/{telegram_user_id}", response_model=ClientResponse)
def get_client_by_telegram(
    telegram_user_id: str,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_tid = tenant_id if current_user.primary_role == "superadmin" else current_user.tenant_id
    client = client_repository.get_client_by_telegram_id(db, telegram_user_id, tenant_id=effective_tid)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    client = client_repository.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if current_user.primary_role != "superadmin" and client.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    existing = client_repository.get_client(db, client_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if current_user.primary_role != "superadmin" and existing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    updated = client_repository.update_client(db, client_id, client)
    return updated


@router.patch("/{client_id}/archive", response_model=ClientResponse)
def archive_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    existing = client_repository.get_client(db, client_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if current_user.primary_role != "superadmin" and existing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    existing.status = "archived"
    existing.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(existing)
    return existing


@router.patch("/{client_id}/restore", response_model=ClientResponse)
def restore_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    existing = client_repository.get_client(db, client_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if current_user.primary_role != "superadmin" and existing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    existing.status = "active"
    existing.archived_at = None
    existing.deleted_at = None
    db.commit()
    db.refresh(existing)
    return existing


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    existing = client_repository.get_client(db, client_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if current_user.primary_role != "superadmin" and existing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    if _client_has_history(db, client_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CLIENT_HISTORY_MESSAGE)
    client_repository.delete_client(db, client_id)
