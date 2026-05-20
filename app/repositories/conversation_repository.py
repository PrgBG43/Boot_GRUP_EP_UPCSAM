from typing import Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


def list_conversations(db: Session, skip: int = 0, limit: int = 100, tenant_id: Optional[int] = None):
    query = db.query(Conversation)
    if tenant_id is not None:
        query = query.filter(Conversation.tenant_id == tenant_id)
    return query.order_by(Conversation.last_interaction_at.desc()).offset(skip).limit(limit).all()


def create_conversation(db: Session, conversation_in: ConversationCreate):
    conversation = Conversation(**conversation_in.model_dump(exclude_none=True))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: int):
    return (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )


def update_conversation(db: Session, conversation_id: int, conversation_in: ConversationUpdate):
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        return None
    data = conversation_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(conversation, key, value)
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation_id: int):
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        return None
    db.delete(conversation)
    db.commit()
    return conversation
