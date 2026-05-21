"""Turnix: punto de entrada de la aplicación FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import create_tables

app = FastAPI(
    title="Turnix - Sistema de Gestión de Citas para Negocios de Belleza",
    description=(
        "API REST para gestionar citas, servicios, clientes y conversaciones "
        "de negocios del sector de belleza mediante Telegram."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS robusta
origins = [
    settings.FRONTEND_URL.rstrip("/"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Crea las tablas en la base de datos al iniciar la aplicación."""
    create_tables()


@app.get("/health", tags=["Health"])
def health_check():
    """Verifica que el backend está activo."""
    return {"status": "ok", "message": "Turnix API funcionando correctamente"}


app.include_router(api_router, prefix="/api/v1")
