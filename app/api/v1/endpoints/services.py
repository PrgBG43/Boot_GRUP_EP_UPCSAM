from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.repositories import service_repository

router = APIRouter()


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate, db: Session = Depends(get_db)):
    return service_repository.create_service(db, service)


@router.get("/", response_model=List[ServiceResponse])
def list_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return service_repository.list_services(db, skip=skip, limit=limit)


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = service_repository.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, service: ServiceUpdate, db: Session = Depends(get_db)):
    updated = service_repository.update_service(db, service_id, service)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return updated


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    deleted = service_repository.delete_service(db, service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
