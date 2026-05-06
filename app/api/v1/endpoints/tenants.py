from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_superadmin, require_tenant_admin_or_above
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.person import Person
from app.models.tenant import Tenant
from app.models.plan import Plan
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.schemas.user import UserCreateFull

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    new_tenant = Tenant(**tenant.model_dump())
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return new_tenant


@router.post("/with-admin", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant_with_admin(
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Crea un negocio y su usuario administrador en una sola operación.
    Payload esperado:
    {
      "tenant": { nombre, descripción, teléfono, dirección, ciudad, horarios, plan, slug, ... },
      "admin": { first_name, last_name, email, password }
    }
    """
    tenant_data = payload.get("tenant", {})
    admin_data  = payload.get("admin", {})

    if not admin_data.get("email") or not admin_data.get("password"):
        raise HTTPException(status_code=400, detail="Se requiere email y contraseña para el administrador")

    # Crear tenant
    new_tenant = Tenant(**{k: v for k, v in tenant_data.items() if hasattr(Tenant, k)})
    db.add(new_tenant)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Slug ya existe. Elige otro identificador.")

    # Crear persona
    person = Person(
        first_name=admin_data.get("first_name", "Admin"),
        last_name=admin_data.get("last_name", ""),
        phone=admin_data.get("phone"),
    )
    db.add(person)
    db.flush()

    # Crear usuario admin
    new_user = User(
        person_id=person.id,
        tenant_id=new_tenant.id,
        email=admin_data["email"],
        password_hash=hash_password(admin_data["password"]),
        is_active=True,
    )
    db.add(new_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email del administrador ya existe")

    # Asignar rol tenant_admin
    role = db.query(Role).filter(Role.name == "tenant_admin").first()
    if role:
        new_user.roles = [role]

    # Vincular owner
    new_tenant.owner_user_id = new_user.id
    db.commit()
    db.refresh(new_tenant)
    return new_tenant



@router.get("/", response_model=List[TenantResponse])
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    return db.query(Tenant).offset(skip).limit(limit).all()


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    if current_user.primary_role == "superadmin":
        raise HTTPException(status_code=400, detail="Superadmin no tiene un tenant propio. Usa /businesses/{id}")
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Usuario sin tenant asignado")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Superadmin puede ver cualquier tenant; tenant_admin solo el suyo
    if current_user.primary_role != "superadmin" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_in: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    if current_user.primary_role == "tenant_admin" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes editar tu propio negocio")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    data = tenant_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/activate", response_model=TenantResponse)
def activate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    tenant.is_active = True
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/deactivate", response_model=TenantResponse)
def deactivate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    tenant.is_active = False
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/plan", response_model=TenantResponse)
def assign_plan(
    tenant_id: int,
    plan_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    plan = db.query(Plan).filter(Plan.name == plan_name).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' no encontrado")
    tenant.plan_id = plan.id
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    db.delete(tenant)
    db.commit()
