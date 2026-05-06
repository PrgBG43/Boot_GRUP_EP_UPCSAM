"""Dependencias de autenticacion y autorizacion para FastAPI."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _load_user(token: str, db: Session) -> Optional[User]:
    payload = decode_token(token)
    if not payload:
        return None
    user_id: int = payload.get("sub")
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user = _load_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado o token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    return _load_user(token, db)


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.primary_role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol superadmin")
    return current_user


def require_tenant_admin_or_above(current_user: User = Depends(get_current_user)) -> User:
    if current_user.primary_role not in ("superadmin", "tenant_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol administrador")
    return current_user


def require_staff_or_above(current_user: User = Depends(get_current_user)) -> User:
    if current_user.primary_role not in ("superadmin", "tenant_admin", "staff"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere acceso de personal")
    return current_user


def get_tenant_id_for_user(current_user: User) -> Optional[int]:
    """Retorna el tenant_id del usuario actual. Superadmin retorna None (acceso global)."""
    if current_user.primary_role == "superadmin":
        return None
    return current_user.tenant_id
