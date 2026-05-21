from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate
from app.services.telegram_token_service import encrypt_token, mask_token


def list_channels(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Channel).offset(skip).limit(limit).all()


def create_channel(db: Session, channel_in: ChannelCreate):
    data = channel_in.model_dump()
    token = data.pop("bot_token")
    channel = Channel(**data, bot_token_encrypted=encrypt_token(token), bot_token_masked=mask_token(token))
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
    raw_token = data.pop("bot_token", None)
    if raw_token:
        channel.bot_token_encrypted = encrypt_token(raw_token)
        channel.bot_token_masked = mask_token(raw_token)
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
