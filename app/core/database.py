from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Para SQLite se necesita check_same_thread=False
connect_args = {}
if settings.db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia para los endpoints (sesión de DB)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea todas las tablas en la base de datos (útil para desarrollo con SQLite)."""
    import app.models  # noqa: F401 – importar todos los modelos antes de crear tablas
    Base.metadata.create_all(bind=engine)