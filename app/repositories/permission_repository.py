from sqlalchemy.orm import Session

from app.models.user import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


def list_permissions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Permission).offset(skip).limit(limit).all()


def create_permission(db: Session, permission_in: PermissionCreate):
    permission = Permission(**permission_in.model_dump())
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def get_permission(db: Session, permission_id: int):
    return db.query(Permission).filter(Permission.id == permission_id).first()


def update_permission(db: Session, permission_id: int, permission_in: PermissionUpdate):
    permission = get_permission(db, permission_id)
    if not permission:
        return None
    data = permission_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(permission, key, value)
    db.commit()
    db.refresh(permission)
    return permission


def delete_permission(db: Session, permission_id: int):
    permission = get_permission(db, permission_id)
    if not permission:
        return None
    db.delete(permission)
    db.commit()
    return permission
