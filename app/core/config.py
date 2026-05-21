"""Configuración de la aplicación cargada desde variables de entorno."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variables de entorno de la aplicación."""

    # Base de datos
    DATABASE_URL: str = "sqlite:///./turnix.db"

    # PostgreSQL opcional
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = "5432"
    POSTGRES_DB: Optional[str] = None

    # JWT / Seguridad
    SECRET_KEY: str = "changeme-turnix-secret-key-2026-demo"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Superadmin inicial y datos demo
    TURNIX_SUPERADMIN_EMAIL: str = "admin@turnix.com"
    TURNIX_SUPERADMIN_PASSWORD: str = "Admin123*"
    TURNIX_SUPERADMIN_FIRST_NAME: str = "Administrador"
    TURNIX_SUPERADMIN_LAST_NAME: str = "Turnix"
    TURNIX_DEMO_SEED: bool = False

    # Telegram Bot global
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def db_url(self) -> str:
        """Devuelve la URL de conexión a la base de datos activa."""
        if all(
            [
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
                self.POSTGRES_HOST,
                self.POSTGRES_DB,
            ]
        ):
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self.DATABASE_URL

    @property
    def is_default_secret_key(self) -> bool:
        """Indica si se usa la llave JWT de desarrollo."""
        return self.SECRET_KEY == "changeme-turnix-secret-key-2026-demo"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
