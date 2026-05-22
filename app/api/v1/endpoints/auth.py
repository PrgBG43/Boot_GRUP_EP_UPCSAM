"""Endpoints de autenticación: login y perfil del usuario actual."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse

router = APIRouter()


def _build_token_response(user: User) -> TokenResponse:
    token = create_access_token({"sub": str(user.id)})
    tenant_name = None
    if user.tenant:
        tenant_name = user.tenant.name
    full_name = None
    if user.person:
        full_name = f"{user.person.first_name} {user.person.last_name}"
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.primary_role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
    )


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacta al administrador.",
        )
    return _build_token_response(user)


# Compatibilidad con OAuth2PasswordRequestForm (para /docs Swagger)
@router.post("/token", include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return _build_token_response(user)


@router.get("/me", response_model=UserMeResponse, summary="Usuario actual")
def get_me(current_user: User = Depends(get_current_user)):
    tenant_name = None
    if current_user.tenant:
        tenant_name = current_user.tenant.name
    full_name = None
    if current_user.person:
        full_name = f"{current_user.person.first_name} {current_user.person.last_name}"
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.primary_role,
        is_active=current_user.is_active,
        tenant_id=current_user.tenant_id,
        tenant_name=tenant_name,
        full_name=full_name,
    )
