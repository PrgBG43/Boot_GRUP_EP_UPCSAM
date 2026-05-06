"""Configuracion del motor de base de datos, sesion y utilidades."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# SQLite requiere check_same_thread=False para uso con FastAPI
connect_args = {}
if settings.db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia FastAPI: crea una sesion de DB y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea todas las tablas definidas en los modelos (util con SQLite)."""
    import app.models  # noqa: F401 – importar todos los modelos antes de crear tablas
    Base.metadata.create_all(bind=engine)
