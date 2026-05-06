"""Router principal de la API v1 – registra todos los sub-routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    channels,
    cities,
    conversations,
    permissions,
    persons,
    roles,
    services,
    states,
    tenants,
    users,
    clients,
    appointments,
    availability,
)

api_router = APIRouter()

# Recursos geograficos
api_router.include_router(states.router, prefix="/states", tags=["States"])
api_router.include_router(cities.router, prefix="/cities", tags=["Cities"])

# Usuarios y autenticacion
api_router.include_router(persons.router, prefix="/persons", tags=["Persons"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])

# Negocio (Tenant)
api_router.include_router(tenants.router, prefix="/businesses", tags=["Businesses"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])

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
