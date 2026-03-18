from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Usamos la propiedad que definimos en settings
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para los endpoints (el famoso DB session)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()