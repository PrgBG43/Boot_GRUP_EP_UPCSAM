from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_staff_or_above, require_superadmin
from app.core.database import get_db
from app.core.security import hash_password
from app.core.slug import ensure_unique_slug
from app.models.location import City
from app.models.person import Person
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.user import Role, User
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate, TenantWithAdminCreate
from app.services.pagination import clamp_page, clamp_page_size, paginate_query
from app.services.plan_usage_service import get_plan_usage_summary

router = APIRouter()

PLAN_ALIASES = {
    "free": "free",
    "gratuito": "free",
    "premium": "premium",
}
ALL_PLAN_VALUES = {"", "all", "todos", "todo"}
PUBLIC_PLAN_NAMES = ("free", "premium")


def _normalize_plan_filter(plan: Optional[str]) -> Optional[str]:
    if plan is None:
        return None
    value = plan.strip().lower()
    if value in ALL_PLAN_VALUES:
        return None
    if value not in PLAN_ALIASES:
        raise HTTPException(status_code=400, detail="Filtro de plan inválido.")
    return PLAN_ALIASES[value]


def _get_city_for_business(db: Session, state_id: Optional[int], city_id: Optional[int]) -> Optional[City]:
    if city_id is None:
        return None
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=400, detail="Selecciona una ciudad.")
    if state_id is not None and city.state_id != state_id:
        raise HTTPException(status_code=400, detail="La ciudad no pertenece al departamento seleccionado.")
    return city


def _get_plan(db: Session, plan_id: Optional[int]) -> Optional[Plan]:
    if plan_id is None:
        raise HTTPException(status_code=400, detail="Selecciona un plan.")
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.is_active == True,
        Plan.name.in_(PUBLIC_PLAN_NAMES),
    ).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Selecciona un plan.")
    return plan


def _tenant_payload(db: Session, tenant: Tenant) -> dict:
    payload = TenantResponse.model_validate(tenant).model_dump(mode="json")
    payload["plan_usage"] = get_plan_usage_summary(db, tenant.id)
    return payload


def _sort_tenants(query, sort_by: str, sort_order: str):
    sortable = {
        "id": Tenant.id,
        "name": Tenant.name,
        "created_at": Tenant.created_at,
        "status": Tenant.status,
    }
    column = sortable.get(sort_by, Tenant.id)
    return query.order_by(column.asc() if sort_order == "asc" else column.desc())


def _tenant_response_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negocio no encontrado.")


@router.get("/")
def list_businesses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    search: Optional[str] = Query(None),
    sort_by: str = Query("id"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    plan: Optional[str] = Query(None, description="free/gratuito, premium o todos"),
    status_filter: Optional[str] = Query(None, alias="status"),
    near_limit: bool = Query(False),
    limit_reached: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Superadmin lista negocios con paginacion, filtros y uso del plan."""
    if skip is not None:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size

    query = (
        db.query(Tenant)
        .filter(or_(Tenant.is_test_environment == False, Tenant.is_test_environment.is_(None)))
        .filter(Tenant.plan.has(Plan.name.in_(PUBLIC_PLAN_NAMES)))
    )
    normalized_plan = _normalize_plan_filter(plan)
    if normalized_plan:
        query = query.join(Plan, Tenant.plan_id == Plan.id).filter(Plan.name == normalized_plan)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Tenant.name.ilike(term))
            | (Tenant.phone.ilike(term))
            | (Tenant.city.ilike(term))
            | (Tenant.slug.ilike(term))
        )

    status_value = (status_filter or "").strip().lower()
    if status_value in {"archived", "archivado"}:
        query = query.filter(Tenant.status == "archived")
    elif status_value in {"inactive", "inactivo"}:
        query = query.filter(or_(Tenant.status != "archived", Tenant.status.is_(None)), Tenant.is_active == False)
    elif status_value in {"active", "activo"}:
        query = query.filter(or_(Tenant.status != "archived", Tenant.status.is_(None)), Tenant.is_active == True)
    elif status_value not in {"all", "todos", "todo"}:
        query = query.filter(or_(Tenant.status != "archived", Tenant.status.is_(None)))

    query = _sort_tenants(query, sort_by, sort_order)

    page = clamp_page(page)
    page_size = clamp_page_size(page_size)

    if near_limit or limit_reached:
        candidates = query.all()
        filtered = []
        for tenant in candidates:
            usage = get_plan_usage_summary(db, tenant.id)
            if near_limit and not usage["near_limit"]:
                continue
            if limit_reached and not usage["limit_reached"]:
                continue
            payload = TenantResponse.model_validate(tenant).model_dump(mode="json")
            payload["plan_usage"] = usage
            filtered.append(payload)
        total = len(filtered)
        start = (page - 1) * page_size
        return {
            "items": filtered[start:start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }

    page_data = paginate_query(query, page, page_size)
    return {**page_data, "items": [_tenant_payload(db, item) for item in page_data["items"]]}


@router.get("/me", response_model=TenantResponse)
def get_my_business(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    """Devuelve el negocio asignado al usuario autenticado."""
    if current_user.primary_role == "superadmin":
        raise HTTPException(status_code=400, detail="Superadmin no tiene negocio propio. Usa /businesses/{id}.")
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Usuario sin negocio asignado.")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role != "superadmin" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    return tenant


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_business(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    data = tenant.model_dump()
    city = _get_city_for_business(db, data.get("state_id"), data.get("city_id"))
    _get_plan(db, data.get("plan_id"))

    base_slug = data.get("slug") or data["name"]
    data["slug"] = ensure_unique_slug(db, base_slug)
    if city:
        data["city"] = city.description

    new_tenant = Tenant(**data)
    if not new_tenant.status:
        new_tenant.status = "active" if new_tenant.is_active else "inactive"
    db.add(new_tenant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No fue posible crear el negocio. Verifica los datos.")
    db.refresh(new_tenant)
    return new_tenant


@router.post("/with-admin", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_business_with_admin(
    payload: TenantWithAdminCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Crea un negocio y su administrador en una transacción."""
    business = payload.business
    admin = payload.admin

    if db.query(User).filter(User.email == str(admin.email)).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    city = _get_city_for_business(db, business.state_id, business.city_id)
    _get_plan(db, business.plan_id)

    final_slug = ensure_unique_slug(db, business.slug or business.name)
    new_tenant = Tenant(
        name=business.name,
        slug=final_slug,
        description=business.description,
        phone=business.phone,
        address=business.address,
        city=city.description,
        state_id=business.state_id,
        city_id=business.city_id,
        opening_time=business.opening_time,
        closing_time=business.closing_time,
        weekly_schedule=business.weekly_schedule,
        base_slot_minutes=business.base_slot_minutes,
        min_booking_notice_minutes=business.min_booking_notice_minutes,
        max_booking_days=business.max_booking_days,
        blocked_dates=business.blocked_dates,
        blocked_time_ranges=business.blocked_time_ranges,
        plan_id=business.plan_id,
        is_active=business.is_active,
        is_test_environment=business.is_test_environment,
        status="active" if business.is_active else "inactive",
    )
    db.add(new_tenant)

    role = db.query(Role).filter(Role.name == "tenant_admin").first()
    if not role:
        raise HTTPException(status_code=500, detail="Rol tenant_admin no existe.")

    try:
        db.flush()
        person = Person(first_name=admin.first_name, last_name=admin.last_name, phone=admin.phone)
        db.add(person)
        db.flush()

        admin_user = User(
            person_id=person.id,
            tenant_id=new_tenant.id,
            email=str(admin.email),
            password_hash=hash_password(admin.password),
            is_active=True,
        )
        admin_user.roles = [role]
        db.add(admin_user)
        db.flush()
        new_tenant.owner_user_id = admin_user.id
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    except Exception:
        db.rollback()
        raise

    db.refresh(new_tenant)
    return new_tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_business(
    tenant_id: int,
    tenant_in: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    if current_user.primary_role == "tenant_admin" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes editar tu propio negocio.")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()

    data = tenant_in.model_dump(exclude_unset=True)
    if current_user.primary_role == "tenant_admin":
        data.pop("plan_id", None)
        data.pop("status", None)
        data.pop("is_active", None)
        data.pop("is_test_environment", None)
    if "plan_id" in data:
        _get_plan(db, data.get("plan_id"))

    next_state_id = data.get("state_id", tenant.state_id)
    next_city_id = data.get("city_id", tenant.city_id)
    if "city_id" in data or "state_id" in data:
        city = _get_city_for_business(db, next_state_id, next_city_id)
        data["city"] = city.description if city else None

    if "slug" in data and data["slug"]:
        data["slug"] = ensure_unique_slug(db, data["slug"], exclude_tenant_id=tenant_id)
    elif not tenant.slug:
        data["slug"] = ensure_unique_slug(db, data.get("name") or tenant.name, exclude_tenant_id=tenant_id)

    for key, value in data.items():
        setattr(tenant, key, value)

    if "is_active" in data and "status" not in data and tenant.status != "archived":
        tenant.status = "active" if tenant.is_active else "inactive"

    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/activate", response_model=TenantResponse)
def activate_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    tenant.is_active = True
    tenant.status = "active"
    tenant.archived_at = None
    tenant.deleted_at = None
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/deactivate", response_model=TenantResponse)
def deactivate_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    tenant.is_active = False
    if tenant.status != "archived":
        tenant.status = "inactive"
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
        raise _tenant_response_not_found()

    normalized_plan = _normalize_plan_filter(plan_name)
    if not normalized_plan:
        raise HTTPException(status_code=400, detail="Selecciona un plan.")
    plan = db.query(Plan).filter(Plan.name == normalized_plan, Plan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")

    tenant.plan_id = plan.id
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/archive", response_model=TenantResponse)
def archive_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    tenant.is_active = False
    tenant.status = "archived"
    tenant.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/restore", response_model=TenantResponse)
def restore_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    tenant.is_active = True
    tenant.status = "active"
    tenant.archived_at = None
    tenant.deleted_at = None
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}/usage")
def get_business_usage(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    if current_user.primary_role != "superadmin" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    return get_plan_usage_summary(db, tenant_id)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise _tenant_response_not_found()
    tenant.is_active = False
    tenant.status = "archived"
    tenant.archived_at = datetime.now(timezone.utc)
    db.commit()
