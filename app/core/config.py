from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos: SQLite por defecto, PostgreSQL si se configuran las variables
    DATABASE_URL: str = "sqlite:///./turnix.db"

    # PostgreSQL (opcional)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Negocio por defecto
    DEFAULT_BUSINESS_NAME: str = "Turnix Demo Barbería"

    # Servidor
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def db_url(self) -> str:
        """Retorna PostgreSQL si están configuradas las variables, de lo contrario SQLite."""
        if (
            self.POSTGRES_USER
            and self.POSTGRES_PASSWORD
            and self.POSTGRES_DB
            and self.POSTGRES_HOST
        ):
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self.DATABASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()