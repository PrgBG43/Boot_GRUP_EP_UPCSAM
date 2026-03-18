from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.person import PersonCreate, PersonResponse, PersonUpdate
from app.repositories import person_repository

router = APIRouter()


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(person: PersonCreate, db: Session = Depends(get_db)):
    return person_repository.create_person(db, person)


@router.get("/", response_model=List[PersonResponse])
def list_persons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return person_repository.list_persons(db, skip=skip, limit=limit)


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = person_repository.get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.put("/{person_id}", response_model=PersonResponse)
def update_person(person_id: int, person: PersonUpdate, db: Session = Depends(get_db)):
    updated = person_repository.update_person(db, person_id, person)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return updated


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    deleted = person_repository.delete_person(db, person_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
