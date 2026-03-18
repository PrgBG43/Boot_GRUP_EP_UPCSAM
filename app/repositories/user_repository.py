from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import Permission, Role, User
from app.schemas.user import UserCreate, UserUpdate


def list_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def _attach_roles_permissions(
    db: Session, user: User, role_ids: Optional[List[int]], permission_ids: Optional[List[int]]
):
    if role_ids:
        roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
        user.roles = roles
    if permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        user.permissions = permissions


def create_user(db: Session, user_in: UserCreate):
    data = user_in.model_dump(exclude={"role_ids", "permission_ids"})
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    _attach_roles_permissions(db, user, user_in.role_ids, user_in.permission_ids)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, user_in: UserUpdate):
    user = get_user(db, user_id)
    if not user:
        return None
    data = user_in.model_dump(exclude_unset=True, exclude={"role_ids", "permission_ids"})
    for key, value in data.items():
        setattr(user, key, value)
    if user_in.role_ids is not None or user_in.permission_ids is not None:
        _attach_roles_permissions(db, user, user_in.role_ids, user_in.permission_ids)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    if not user:
        return None
    db.delete(user)
    db.commit()
    return user
