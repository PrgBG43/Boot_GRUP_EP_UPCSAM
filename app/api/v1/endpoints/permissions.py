from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate
from app.repositories import permission_repository

router = APIRouter()


@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(permission: PermissionCreate, db: Session = Depends(get_db)):
    try:
        return permission_repository.create_permission(db, permission)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission name must be unique")


@router.get("/", response_model=List[PermissionResponse])
def list_permissions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return permission_repository.list_permissions(db, skip=skip, limit=limit)


@router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(permission_id: int, db: Session = Depends(get_db)):
    permission = permission_repository.get_permission(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return permission


@router.put("/{permission_id}", response_model=PermissionResponse)
def update_permission(permission_id: int, permission: PermissionUpdate, db: Session = Depends(get_db)):
    try:
        updated = permission_repository.update_permission(db, permission_id, permission)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission name must be unique")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return updated


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    deleted = permission_repository.delete_permission(db, permission_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
