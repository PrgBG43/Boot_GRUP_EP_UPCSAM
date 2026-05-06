from sqlalchemy.orm import Session

from app.models.message import Message
from app.schemas.message import MessageCreate


def list_messages_by_conversation(db: Session, conversation_id: int):
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )


def create_message(db: Session, message_in: MessageCreate):
    message = Message(**message_in.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_message(db: Session, message_id: int):
    return db.query(Message).filter(Message.id == message_id).first()
