from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_tenant_admin_or_above
from app.models.user import User
from app.models.service import Service
from app.models.tenant import Tenant
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate

router = APIRouter()


def _check_plan_service_limit(db: Session, tenant_id: int):
    """Verifica que el tenant no supere el límite de servicios activos según su plan."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not tenant.plan:
        return  # Sin plan asignado: permitir
    max_services = tenant.plan.max_active_services
    if max_services is None:
        return  # Ilimitado
    active_count = (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.is_active == True)
        .count()
    )
    if active_count >= max_services:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Límite del plan alcanzado: máximo {max_services} servicios activos "
                f"en el plan '{tenant.plan.display_name}'. Desactiva un servicio o cambia de plan."
            ),
        )


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    # Verificar que el tenant corresponde al usuario
    if current_user.primary_role != "superadmin" and current_user.tenant_id != service.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes crear servicios en otro negocio")
    if service.is_active:
        _check_plan_service_limit(db, service.tenant_id)
    new_service = Service(**service.model_dump())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service


@router.get("/", response_model=List[ServiceResponse])
def list_services(
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Service)
    if current_user.primary_role == "superadmin":
        if tenant_id:
            query = query.filter(Service.tenant_id == tenant_id)
    else:
        query = query.filter(Service.tenant_id == current_user.tenant_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if current_user.primary_role != "superadmin" and service.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_in: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if current_user.primary_role != "superadmin" and service.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    # Verificar límite si se va a activar
    if service_in.is_active is True and not service.is_active:
        _check_plan_service_limit(db, service.tenant_id)
    data = service_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if current_user.primary_role != "superadmin" and service.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    db.delete(service)
    db.commit()
