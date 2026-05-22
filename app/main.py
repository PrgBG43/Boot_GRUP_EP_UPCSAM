"""Turnix: punto de entrada de la aplicación FastAPI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.bot.telegram_bot import TelegramBotManager, set_telegram_bot_manager
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

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def on_startup():
    """Crea tablas e inicia servicios de background al iniciar la aplicación."""
    print("Iniciando Turnix...")
    create_tables()
    manager = TelegramBotManager()
    app.state.telegram_bot_manager = manager
    set_telegram_bot_manager(manager)
    try:
        await manager.start()
    except Exception as exc:
        print(f"Servicio Telegram: no se pudo iniciar automáticamente: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
    """Detiene servicios de background de forma ordenada."""
    manager = getattr(app.state, "telegram_bot_manager", None)
    if manager:
        await manager.stop()
    set_telegram_bot_manager(None)
    print("Servicio Telegram detenido correctamente.")


@app.get("/health", tags=["Health"])
def health_check():
    """Verifica que el backend está activo."""
    return {"status": "ok", "message": "Turnix API funcionando correctamente"}


app.include_router(api_router, prefix="/api/v1")
