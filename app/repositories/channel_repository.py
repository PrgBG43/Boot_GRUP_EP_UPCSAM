from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate


def list_channels(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Channel).offset(skip).limit(limit).all()


def create_channel(db: Session, channel_in: ChannelCreate):
    channel = Channel(**channel_in.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def get_channel(db: Session, channel_id: int):
    return db.query(Channel).filter(Channel.id == channel_id).first()


def update_channel(db: Session, channel_id: int, channel_in: ChannelUpdate):
    channel = get_channel(db, channel_id)
    if not channel:
        return None
    data = channel_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(channel, key, value)
    db.commit()
    db.refresh(channel)
    return channel


def delete_channel(db: Session, channel_id: int):
    channel = get_channel(db, channel_id)
    if not channel:
        return None
    db.delete(channel)
    db.commit()
    return channel
