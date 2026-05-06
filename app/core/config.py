"""Configuracion de la aplicacion cargada desde variables de entorno."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variables de entorno de la aplicacion."""

    # Base de datos
    DATABASE_URL: str = "sqlite:///./turnix.db"

    # PostgreSQL (opcional – usa estas variables si quieres Postgres)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = "5432"
    POSTGRES_DB: Optional[str] = None

    # JWT / Seguridad
    SECRET_KEY: str = "changeme-turnix-secret-key-2026-demo"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas para demo

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def db_url(self) -> str:
        """Devuelve la URL de conexion a la base de datos activa."""
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
