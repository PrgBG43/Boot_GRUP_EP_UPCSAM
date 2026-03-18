from sqlalchemy.orm import Session

from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate


def list_services(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Service).offset(skip).limit(limit).all()


def create_service(db: Session, service_in: ServiceCreate):
    service = Service(**service_in.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def get_service(db: Session, service_id: int):
    return db.query(Service).filter(Service.id == service_id).first()


def update_service(db: Session, service_id: int, service_in: ServiceUpdate):
    service = get_service(db, service_id)
    if not service:
        return None
    data = service_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service_id: int):
    service = get_service(db, service_id)
    if not service:
        return None
    db.delete(service)
    db.commit()
    return service
