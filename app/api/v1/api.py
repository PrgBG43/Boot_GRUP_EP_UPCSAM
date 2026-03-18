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
)

api_router = APIRouter()

api_router.include_router(states.router, prefix="/states", tags=["States"])
api_router.include_router(cities.router, prefix="/cities", tags=["Cities"])
api_router.include_router(persons.router, prefix="/persons", tags=["Persons"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])
api_router.include_router(services.router, prefix="/services", tags=["Services"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
