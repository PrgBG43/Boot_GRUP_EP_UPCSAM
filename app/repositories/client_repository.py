from typing import Optional
from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


def list_clients(db: Session, skip: int = 0, limit: int = 100, tenant_id: Optional[int] = None):
    query = db.query(Client)
    if tenant_id is not None:
        query = query.filter(Client.tenant_id == tenant_id)
    return query.offset(skip).limit(limit).all()


def create_client(db: Session, client_in: ClientCreate):
    client = Client(**client_in.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client(db: Session, client_id: int):
    return db.query(Client).filter(Client.id == client_id).first()


def get_client_by_telegram_id(db: Session, telegram_user_id: str, tenant_id: Optional[int] = None):
    query = db.query(Client).filter(Client.telegram_user_id == telegram_user_id)
    if tenant_id is not None:
        query = query.filter(Client.tenant_id == tenant_id)
    return query.first()


def update_client(db: Session, client_id: int, client_in: ClientUpdate):
    client = get_client(db, client_id)
    if not client:
        return None
    for key, value in client_in.model_dump(exclude_unset=True).items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, client_id: int):
    client = get_client(db, client_id)
    if not client:
        return None
    db.delete(client)
    db.commit()
    return client

