from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageCreate, MessageResponse
from app.repositories import conversation_repository, message_repository

router = APIRouter()


@router.get("/", response_model=List[ConversationResponse])
def list_conversations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return conversation_repository.list_conversations(db, skip=skip, limit=limit)


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(conversation: ConversationCreate, db: Session = Depends(get_db)):
    return conversation_repository.create_conversation(db, conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: int, conversation: ConversationUpdate, db: Session = Depends(get_db)):
    updated = conversation_repository.update_conversation(db, conversation_id, conversation)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    deleted = conversation_repository.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return message_repository.list_messages_by_conversation(db, conversation_id)


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    conversation = conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return message_repository.create_message(db, message)
