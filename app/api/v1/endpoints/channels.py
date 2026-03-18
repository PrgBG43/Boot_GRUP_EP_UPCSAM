from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.channel import ChannelCreate, ChannelResponse, ChannelUpdate
from app.repositories import channel_repository

router = APIRouter()


@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    return channel_repository.create_channel(db, channel)


@router.get("/", response_model=List[ChannelResponse])
def list_channels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return channel_repository.list_channels(db, skip=skip, limit=limit)


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = channel_repository.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, channel: ChannelUpdate, db: Session = Depends(get_db)):
    updated = channel_repository.update_channel(db, channel_id, channel)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return updated


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    deleted = channel_repository.delete_channel(db, channel_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
