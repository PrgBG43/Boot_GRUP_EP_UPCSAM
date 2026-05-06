from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_superadmin, require_tenant_admin_or_above
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.person import Person
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserCreateFull

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Superadmin ve todos los usuarios (con filtro opcional por tenant_id).
    Tenant_admin ve solo los usuarios de su tenant.
    """
    query = db.query(User)
    if current_user.primary_role == "superadmin":
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        query = query.filter(User.tenant_id == current_user.tenant_id)
    return query.offset(skip).limit(limit).all()


@router.get("/staff", response_model=List[UserResponse])
def list_staff(
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Lista el personal (staff) del tenant.
    Superadmin debe pasar tenant_id como query param.
    Tenant_admin lista el staff de su propio tenant.
    """
    if current_user.primary_role == "superadmin":
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Superadmin debe especificar tenant_id")
        tid = tenant_id
    else:
        tid = current_user.tenant_id

    return (
        db.query(User)
        .filter(User.tenant_id == tid)
        .filter(User.roles.any(Role.name == "staff"))
        .all()
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreateFull,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Superadmin puede crear usuarios en cualquier tenant.
    Tenant_admin solo puede crear staff en su propio tenant.
    """
    if current_user.primary_role == "tenant_admin":
        if user.role_name not in ("staff", "customer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Como administrador de negocio solo puedes crear personal (staff)",
            )
        user = user.model_copy(update={"tenant_id": current_user.tenant_id})

    person = Person(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
    )
    db.add(person)
    db.flush()

    hashed = hash_password(user.password)
    new_user = User(
        person_id=person.id,
        tenant_id=user.tenant_id,
        email=user.email,
        password_hash=hashed,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya existe")

    if user.role_name:
        role = db.query(Role).filter(Role.name == user.role_name).first()
        if role:
            new_user.roles = [role]

    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin") and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role not in ("superadmin", "tenant_admin") and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    data = user_in.model_dump(exclude_unset=True, exclude={"role_ids", "password"})
    if user_in.password:
        data["password_hash"] = hash_password(user_in.password)
    for key, value in data.items():
        setattr(user, key, value)
    if user_in.role_ids is not None and current_user.primary_role == "superadmin":
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()
        user.roles = roles
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya existe")
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()



@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreateFull,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Superadmin puede crear usuarios en cualquier tenant.
    Tenant_admin solo puede crear usuarios (staff/customer) en su propio tenant.
    """
    if current_user.primary_role == "tenant_admin":
        # Forzar tenant_id al propio y solo permitir crear staff/customer
        if user.role_name not in ("staff", "customer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Como administrador de negocio solo puedes crear personal (staff)"
            )
        # Forzar tenant propio
        user = user.model_copy(update={"tenant_id": current_user.tenant_id})

    # Crear person
    person = Person(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
    )
    db.add(person)
    db.flush()

    hashed = hash_password(user.password)
    new_user = User(
        person_id=person.id,
        tenant_id=user.tenant_id,
        email=user.email,
        password_hash=hashed,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya existe")

    # Asignar rol
    if user.role_name:
        role = db.query(Role).filter(Role.name == user.role_name).first()
        if role:
            new_user.roles = [role]

    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """
    Superadmin ve todos los usuarios.
    Tenant_admin ve solo los usuarios de su tenant.
    """
    query = db.query(User)
    if current_user.primary_role != "superadmin":
        query = query.filter(User.tenant_id == current_user.tenant_id)
    return query.offset(skip).limit(limit).all()


@router.get("/staff", response_model=List[UserResponse])
def list_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Lista el personal (staff) del tenant actual."""
    from app.models.user import user_role_table
    if current_user.primary_role == "superadmin":
        raise HTTPException(status_code=400, detail="Especifica un tenant para listar staff")
    staff_role = db.query(Role).filter(Role.name == "staff").first()
    if not staff_role:
        return []
    return (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .filter(User.roles.any(Role.name == "staff"))
        .all()
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role == "superadmin":
        pass
    elif current_user.primary_role == "tenant_admin":
        # puede ver usuarios de su tenant o a sí mismo
        pass
    elif current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    # tenant_admin solo puede ver usuarios de su propio tenant
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role == "superadmin":
        pass
    elif current_user.primary_role == "tenant_admin":
        # puede editar usuarios de su tenant
        pass
    elif current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    data = user_in.model_dump(exclude_unset=True, exclude={"role_ids", "password"})
    if user_in.password:
        data["password_hash"] = hash_password(user_in.password)
    for key, value in data.items():
        setattr(user, key, value)
    if user_in.role_ids is not None and current_user.primary_role == "superadmin":
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()
        user.roles = roles
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya existe")
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.primary_role == "tenant_admin" and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()


@router.get("/", response_model=List[UserResponse])
def list_users_superadmin(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Solo superadmin puede ver a cualquier usuario; los demás solo se ven a sí mismos
    if current_user.primary_role != "superadmin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.primary_role != "superadmin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    data = user_in.model_dump(exclude_unset=True, exclude={"role_ids", "password"})
    if user_in.password:
        data["password_hash"] = hash_password(user_in.password)
    for key, value in data.items():
        setattr(user, key, value)
    if user_in.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()
        user.roles = roles
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya existe")
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
