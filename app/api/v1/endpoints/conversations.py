from typing import List, Optional

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import require_staff_or_above
from app.core.database import get_db
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.telegram_config import TelegramConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories import conversation_repository, message_repository
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageCreate, MessageResponse, MessageSendRequest
from app.services.pagination import paginate_query
from app.services.telegram_token_service import decrypt_token

router = APIRouter()
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
CONVERSATION_HISTORY_MESSAGE = (
    "Esta conversación tiene mensajes asociados. "
    "Puedes archivarla, pero no eliminarla definitivamente."
)


def _assert_conversation_access(current_user: User, conversation) -> None:
    if current_user.primary_role == "superadmin":
        return
    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")


def _send_telegram_message(token: str, chat_id: str, content: str) -> None:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                TELEGRAM_API.format(token=token, method="sendMessage"),
                json={"chat_id": chat_id, "text": content},
            )
        result = response.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible enviar el mensaje por Telegram. Intenta nuevamente.",
        )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("description") or "Telegram no acepto el mensaje.",
        )


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
    else:
        query = query.filter(or_(Conversation.status != "archived", Conversation.status.is_(None)))
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
    if db.query(Message.id).filter(Message.conversation_id == conversation_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CONVERSATION_HISTORY_MESSAGE)
    conversation_repository.delete_conversation(db, conversation_id)


@router.patch("/{conversation_id}/archive", response_model=ConversationResponse)
def archive_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    conversation.status = "archived"
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/restore", response_model=ConversationResponse)
def restore_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)
    conversation.status = "active"
    db.commit()
    db.refresh(conversation)
    return conversation


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


@router.post("/{conversation_id}/reply", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def reply_to_conversation(
    conversation_id: int,
    payload: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    _assert_conversation_access(current_user, conversation)

    if conversation.channel != "telegram":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se pueden responder conversaciones de Telegram.")

    config = (
        db.query(TelegramConfig)
        .filter(
            TelegramConfig.tenant_id == conversation.tenant_id,
            TelegramConfig.is_connected == True,
            TelegramConfig.bot_token_encrypted.isnot(None),
        )
        .first()
    )
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este negocio no tiene un bot de Telegram conectado.")
    if conversation.bot_id and config.bot_id and conversation.bot_id != config.bot_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta conversación pertenece a otro bot de Telegram. Inicia una conversación nueva con el bot conectado.",
        )

    token = decrypt_token(config.bot_token_encrypted)
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fue posible leer el token del bot conectado.")

    _send_telegram_message(token, conversation.chat_id, payload.content)
    conversation.last_interaction_at = datetime.now(timezone.utc)
    return message_repository.create_message(
        db,
        MessageCreate(conversation_id=conversation.id, direction="outgoing", content=payload.content),
    )


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
    if message.conversation_id != conversation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no pertenece a esta conversación.")
    return message_repository.create_message(db, message)
