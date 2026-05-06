"""Configuración de Telegram por negocio."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, require_tenant_admin_or_above
from app.models.user import User
from app.models.telegram_config import TelegramConfig
from app.schemas.telegram_config import TelegramConfigResponse, TelegramConfigUpdate

router = APIRouter()


def _get_tenant_id(current_user: User, tenant_id_param: int = None) -> int:
    if current_user.primary_role == "superadmin":
        if not tenant_id_param:
            raise HTTPException(status_code=400, detail="Superadmin debe especificar tenant_id")
        return tenant_id_param
    return current_user.tenant_id


@router.get("/", response_model=TelegramConfigResponse)
def get_telegram_config(
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Obtiene la configuración de Telegram del negocio."""
    tid = _get_tenant_id(current_user, tenant_id)
    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tid).first()
    if not config:
        # Crear configuración por defecto
        config = TelegramConfig(tenant_id=tid)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/", response_model=TelegramConfigResponse)
def update_telegram_config(
    config_in: TelegramConfigUpdate,
    tenant_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above),
):
    """Actualiza la configuración de Telegram del negocio."""
    tid = _get_tenant_id(current_user, tenant_id)
    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tid).first()
    if not config:
        config = TelegramConfig(tenant_id=tid)
        db.add(config)
        db.flush()

    data = config_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config
