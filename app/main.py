from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import create_tables

app = FastAPI(
    title="Turnix – Sistema de Gestión de Citas para Negocios de Belleza",
    description=(
        "API REST para gestionar citas, servicios, clientes y conversaciones "
        "de negocios del sector de belleza mediante Telegram."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS – permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Crea las tablas en la base de datos al iniciar (útil con SQLite)."""
    create_tables()


@app.get("/health", tags=["Health"])
def health_check():
    """Verifica que el backend está activo."""
    return {"status": "ok", "message": "Turnix API funcionando correctamente"}


app.include_router(api_router, prefix="/api/v1")
