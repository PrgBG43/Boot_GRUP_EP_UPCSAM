from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_tenant_admin_or_above
from app.models.appointment import Appointment
from app.models.user import User
from app.models.service import Service
from app.models.tenant import Tenant
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.services.pagination import paginate_query

router = APIRouter()
SERVICE_HISTORY_MESSAGE = (
    "Este servicio tiene citas asociadas. "
    "Puedes desactivarlo, pero no eliminarlo definitivamente."
)


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


@router.get("/")
def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if skip:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size
    query = db.query(Service)
    if current_user.primary_role == "superadmin":
        if tenant_id:
            query = query.filter(Service.tenant_id == tenant_id)
    else:
        query = query.filter(Service.tenant_id == current_user.tenant_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Service.name.ilike(term), Service.description.ilike(term)))
    if status_filter in {"active", "activo"}:
        query = query.filter(Service.is_active == True)
    elif status_filter in {"inactive", "inactivo"}:
        query = query.filter(Service.is_active == False)
    sortable = {"name": Service.name, "price": Service.price, "duration_minutes": Service.duration_minutes, "id": Service.id}
    column = sortable.get(sort_by, Service.name)
    query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    page_data = paginate_query(query, page, page_size)
    return {
        **page_data,
        "items": [ServiceResponse.model_validate(item).model_dump(mode="json") for item in page_data["items"]],
    }


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
    if db.query(Appointment.id).filter(Appointment.service_id == service.id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=SERVICE_HISTORY_MESSAGE)
    db.delete(service)
    db.commit()
