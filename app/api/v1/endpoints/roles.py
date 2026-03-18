from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.repositories import role_repository

router = APIRouter()


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    try:
        return role_repository.create_role(db, role)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name must be unique")


@router.get("/", response_model=List[RoleResponse])
def list_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return role_repository.list_roles(db, skip=skip, limit=limit)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = role_repository.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    try:
        updated = role_repository.update_role(db, role_id, role)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name must be unique")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return updated


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, db: Session = Depends(get_db)):
    deleted = role_repository.delete_role(db, role_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
