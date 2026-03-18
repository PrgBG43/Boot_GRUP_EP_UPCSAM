from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


def list_tenants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Tenant).offset(skip).limit(limit).all()


def create_tenant(db: Session, tenant_in: TenantCreate):
    new_tenant = Tenant(**tenant_in.model_dump())
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return new_tenant


def get_tenant(db: Session, tenant_id: int):
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def update_tenant(db: Session, tenant_id: int, tenant_in: TenantUpdate):
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        return None
    data = tenant_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return tenant


def delete_tenant(db: Session, tenant_id: int):
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        return None
    db.delete(tenant)
    db.commit()
    return tenant
