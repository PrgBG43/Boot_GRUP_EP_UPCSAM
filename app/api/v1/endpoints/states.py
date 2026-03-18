from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.state import StateCreate, StateResponse, StateUpdate
from app.repositories import state_repository

router = APIRouter()


@router.post("/", response_model=StateResponse, status_code=status.HTTP_201_CREATED)
def create_state(state: StateCreate, db: Session = Depends(get_db)):
    return state_repository.create_state(db, state)


@router.get("/", response_model=List[StateResponse])
def list_states(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return state_repository.list_states(db, skip=skip, limit=limit)


@router.get("/{state_id}", response_model=StateResponse)
def get_state(state_id: int, db: Session = Depends(get_db)):
    state = state_repository.get_state(db, state_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
    return state


@router.put("/{state_id}", response_model=StateResponse)
def update_state(state_id: int, state: StateUpdate, db: Session = Depends(get_db)):
    updated = state_repository.update_state(db, state_id, state)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
    return updated


@router.delete("/{state_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_state(state_id: int, db: Session = Depends(get_db)):
    deleted = state_repository.delete_state(db, state_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
