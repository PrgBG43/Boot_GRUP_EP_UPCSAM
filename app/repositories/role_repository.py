from sqlalchemy.orm import Session

from app.models.user import Role
from app.schemas.role import RoleCreate, RoleUpdate


def list_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Role).offset(skip).limit(limit).all()


def create_role(db: Session, role_in: RoleCreate):
    role = Role(**role_in.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def get_role(db: Session, role_id: int):
    return db.query(Role).filter(Role.id == role_id).first()


def update_role(db: Session, role_id: int, role_in: RoleUpdate):
    role = get_role(db, role_id)
    if not role:
        return None
    data = role_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(role, key, value)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int):
    role = get_role(db, role_id)
    if not role:
        return None
    db.delete(role)
    db.commit()
    return role
