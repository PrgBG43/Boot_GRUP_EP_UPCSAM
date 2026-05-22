from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user, require_superadmin, require_tenant_admin_or_above
from app.core.database import get_db
from app.core.security import hash_password
from app.models.person import Person
from app.models.tenant import Tenant
from app.models.user import Role, User
from app.schemas.user import (
    PasswordReset,
    UserCreateFull,
    UserResponse,
    UserStaffCreate,
    UserUpdate,
)
from app.services.pagination import paginate_query

router = APIRouter()

MANAGEABLE_BY_TENANT_ADMIN = {"staff", "customer"}
VALID_ROLES = {"superadmin", "tenant_admin", "staff", "customer"}


def _role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise HTTPException(status_code=500, detail=f"Rol requerido no existe: {name}")
    return role


def _tenant_exists(db: Session, tenant_id: Optional[int]) -> bool:
    if tenant_id is None:
        return False
    return db.query(Tenant.id).filter(Tenant.id == tenant_id).first() is not None


def _email_available(db: Session, email: str, exclude_user_id: Optional[int] = None) -> bool:
    query = db.query(User).filter(User.email == email)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is None


def _assert_can_manage_user(current_user: User, target: User) -> None:
    if current_user.primary_role == "superadmin":
        return

    if current_user.primary_role != "tenant_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso insuficiente.")

    if target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")

    if target.primary_role not in MANAGEABLE_BY_TENANT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes administrar personal de tu negocio.",
        )


def _create_user_with_person(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role_name: str,
    tenant_id: Optional[int],
    phone: Optional[str] = None,
) -> User:
    if not _email_available(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado.")

    person = Person(first_name=first_name, last_name=last_name, phone=phone)
    db.add(person)
    db.flush()

    new_user = User(
        person_id=person.id,
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )
    new_user.roles = [_role(db, role_name)]
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado.")

    db.refresh(new_user)
    return new_user


@router.get("/")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Lista usuarios según el alcance del rol actual."""
    # Cargamos relaciones necesarias para evitar errores de Lazy Loading durante la serialización
    query = db.query(User).options(
        joinedload(User.person),
        joinedload(User.roles),
        joinedload(User.tenant)
    )
    if skip:
        page = int(skip / (limit or page_size)) + 1
        page_size = limit or page_size
    if current_user.primary_role == "superadmin":
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        query = query.filter(User.tenant_id == current_user.tenant_id)
    if role:
        query = query.filter(User.roles.any(Role.name == role))
    if status_filter in {"active", "activo"}:
        query = query.filter(User.is_active == True)
    elif status_filter in {"inactive", "inactivo"}:
        query = query.filter(User.is_active == False)
    if search:
        term = f"%{search.strip()}%"
        query = query.outerjoin(Person, Person.id == User.person_id).filter(
            or_(User.email.ilike(term), Person.first_name.ilike(term), Person.last_name.ilike(term))
        )
    sortable = {"id": User.id, "email": User.email, "created_at": User.created_at}
    column = sortable.get(sort_by, User.id)
    query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    page_data = paginate_query(query, page, page_size)
    return {
        **page_data,
        "items": [UserResponse.model_validate(item).model_dump(mode="json") for item in page_data["items"]],
    }


@router.get("/staff", response_model=List[UserResponse])
def list_staff(
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Lista personal del negocio."""
    # Aplicamos joinedload también aquí para optimizar la respuesta
    query = db.query(User).options(
        joinedload(User.person),
        joinedload(User.roles),
        joinedload(User.tenant)
    ).filter(User.roles.any(Role.name == "staff"))

    if current_user.primary_role == "superadmin":
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        query = query.filter(User.tenant_id == current_user.tenant_id)
    return query.order_by(User.id).all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreateFull,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Crea usuarios respetando el alcance multi-tenant."""
    role_name = user.role_name or "staff"
    if role_name not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Rol inválido.")

    tenant_id = user.tenant_id
    if current_user.primary_role == "tenant_admin":
        if role_name not in MANAGEABLE_BY_TENANT_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Como administrador de negocio solo puedes crear staff o customer.",
            )
        tenant_id = current_user.tenant_id
    elif role_name != "superadmin":
        if tenant_id is None:
            raise HTTPException(status_code=400, detail="Selecciona un negocio.")
        if not _tenant_exists(db, tenant_id):
            raise HTTPException(status_code=404, detail="Negocio no encontrado.")

    if role_name == "superadmin":
        tenant_id = None

    return _create_user_with_person(
        db,
        first_name=user.first_name,
        last_name=user.last_name,
        email=str(user.email),
        password=user.password,
        role_name=role_name,
        tenant_id=tenant_id,
        phone=user.phone,
    )


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: UserStaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Crea personal con rol staff."""
    if current_user.primary_role == "superadmin":
        if payload.tenant_id is None:
            raise HTTPException(status_code=400, detail="Selecciona un negocio.")
        if not _tenant_exists(db, payload.tenant_id):
            raise HTTPException(status_code=404, detail="Negocio no encontrado.")
        tenant_id = payload.tenant_id
    else:
        tenant_id = current_user.tenant_id

    return _create_user_with_person(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=str(payload.email),
        password=payload.password,
        role_name="staff",
        tenant_id=tenant_id,
        phone=payload.phone,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if current_user.primary_role == "superadmin" or current_user.id == user_id:
        return user
    if current_user.primary_role == "tenant_admin" and user.tenant_id == current_user.tenant_id:
        return user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if current_user.id != user_id:
        _assert_can_manage_user(current_user, user)

    if user_in.email is not None:
        email = str(user_in.email)
        if not _email_available(db, email, exclude_user_id=user_id):
            raise HTTPException(status_code=400, detail="El correo ya está registrado.")
        user.email = email

    if user_in.password:
        user.password_hash = hash_password(user_in.password)

    if user_in.is_active is not None:
        if current_user.primary_role == "tenant_admin" and user.primary_role not in MANAGEABLE_BY_TENANT_ADMIN:
            raise HTTPException(status_code=403, detail="Solo puedes activar o desactivar personal.")
        user.is_active = user_in.is_active

    if user_in.tenant_id is not None and current_user.primary_role == "superadmin":
        if not _tenant_exists(db, user_in.tenant_id):
            raise HTTPException(status_code=404, detail="Negocio no encontrado.")
        user.tenant_id = user_in.tenant_id

    if user_in.role_ids is not None and current_user.primary_role == "superadmin":
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()
        if not roles:
            raise HTTPException(status_code=400, detail="Selecciona al menos un rol válido.")
        user.roles = roles

    if user.person:
        if user_in.first_name is not None:
            user.person.first_name = user_in.first_name.strip()
        if user_in.last_name is not None:
            user.person.last_name = user_in.last_name.strip()
        if user_in.phone is not None:
            user.person.phone = user_in.phone

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    db.refresh(user)
    return user


@router.patch("/{user_id}/reset-password", response_model=UserResponse)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    _assert_can_manage_user(current_user, user)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    _assert_can_manage_user(current_user, user)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    _assert_can_manage_user(current_user, user)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    db.delete(user)
    db.commit()
