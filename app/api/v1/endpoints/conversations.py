from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import require_staff_or_above
from app.core.database import get_db
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories import conversation_repository, message_repository
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageCreate, MessageResponse
from app.services.pagination import paginate_query

router = APIRouter()


def _assert_conversation_access(current_user: User, conversation) -> None:
    if current_user.primary_role == "superadmin":
        return
    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")


@router.get("/")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("last_interaction_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if skip:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size
    effective_tenant = tenant_id if current_user.primary_role == "superadmin" else current_user.tenant_id
    query = db.query(Conversation)
    if effective_tenant is not None:
        query = query.filter(Conversation.tenant_id == effective_tenant)
    if status_filter:
        query = query.filter(Conversation.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        query = (
            query.outerjoin(Client, Client.id == Conversation.client_id)
            .outerjoin(Tenant, Tenant.id == Conversation.tenant_id)
            .filter(or_(Client.full_name.ilike(term), Conversation.chat_id.ilike(term), Tenant.name.ilike(term)))
        )
    sortable = {
        "last_interaction_at": Conversation.last_interaction_at,
        "id": Conversation.id,
        "status": Conversation.status,
    }
    column = sortable.get(sort_by, Conversation.last_interaction_at)
    query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    page_data = paginate_query(query, page, page_size)
    return {
        **page_data,
        "items": [ConversationResponse.model_validate(item).model_dump(mode="json") for item in page_data["items"]],
    }


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if current_user.primary_role != "superadmin" and conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    return conversation_repository.create_conversation(db, conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    conversation: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    existing = conversation_repository.get_conversation(db, conversation_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, existing)
    updated = conversation_repository.update_conversation(db, conversation_id, conversation)
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    conversation_repository.delete_conversation(db, conversation_id)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    return message_repository.list_messages_by_conversation(db, conversation_id)


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(
    conversation_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    return message_repository.create_message(db, message)

