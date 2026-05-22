"""Router principal de la API v1 – registra todos los sub-routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    channels,
    cities,
    conversations,
    dashboard,
    permissions,
    persons,
    plans,
    roles,
    services,
    states,
    tenants,
    users,
    clients,
    appointments,
    availability,
    telegram_config,
)

api_router = APIRouter()

# Autenticación
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Dashboard / métricas
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# Recursos geográficos
api_router.include_router(states.router, prefix="/states", tags=["States"])
api_router.include_router(cities.router, prefix="/cities", tags=["Cities"])

# Usuarios y roles
api_router.include_router(persons.router, prefix="/persons", tags=["Persons"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])

# Planes
api_router.include_router(plans.router, prefix="/plans", tags=["Plans"])

# Negocio (Tenant)
api_router.include_router(tenants.router, prefix="/businesses", tags=["Businesses"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])

# Configuración de Telegram por negocio
api_router.include_router(telegram_config.router, prefix="/telegram-config", tags=["Telegram Config"])

# Servicios del negocio
api_router.include_router(services.router, prefix="/services", tags=["Services"])

# Clientes
api_router.include_router(clients.router, prefix="/clients", tags=["Clients"])

# Citas
api_router.include_router(
    appointments.router, prefix="/appointments", tags=["Appointments"]
)

# Disponibilidad
api_router.include_router(
    availability.router, prefix="/availability", tags=["Availability"]
)

# Conversaciones y mensajes
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["Conversations"]
)

