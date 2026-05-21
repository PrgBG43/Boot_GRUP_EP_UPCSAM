"""Configuracion del motor de base de datos, sesion y utilidades."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

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
    """Crea tablas y agrega columnas nuevas en bases locales existentes."""
    import app.models  # noqa: F401
    from app.core.schema_migrations import ensure_schema_compatibility

    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
