from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.repositories import tenant_repository

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    return tenant_repository.create_tenant(db, tenant)


@router.get("/", response_model=List[TenantResponse])
def list_tenants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return tenant_repository.list_tenants(db, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = tenant_repository.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(tenant_id: int, tenant: TenantUpdate, db: Session = Depends(get_db)):
    updated = tenant_repository.update_tenant(db, tenant_id, tenant)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return updated


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    deleted = tenant_repository.delete_tenant(db, tenant_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
