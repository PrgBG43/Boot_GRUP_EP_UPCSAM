# 📚 Detalle funcional y técnico

## Dominio (MER simplificado)
- **State / City**: ubicación; City FK a State.
- **Person / User**: persona real vs cuenta; User FK único a Person.
- **Role / Permission**: autorización por roles/permisos (tablas puente `role_has_permission`, `user_has_permission`, `user_roles`).
- **Tenant**: cada negocio/cliente (owner_user_id).
- **Channel**: integraciones (ej. Telegram, bot_token).
- **Service**: catálogo de servicios por tenant.
- **Conversation**: interacciones (chat_id string largo, visit_count).

Relaciones clave: State 1–* City; City 1–* Person; Person 1–1 User; User 1–1 Tenant (owner); Tenant 1–* Channel/Service/Conversation.

## Arquitectura por capas
- `app/models`: ORM SQLAlchemy.
- `app/schemas`: Pydantic para entrada/salida (Base/Create/Update/Response).
- `app/repositories`: CRUD y consultas encapsuladas.
- `app/api/v1/endpoints`: routers FastAPI por recurso, registrados en `api.py`.
- `app/core`: config/env y DB session.
- `alembic`: migraciones (script.py.mako + versions).

## Migraciones y orden (resumen)
1. `upgrade head` (aplica pendientes, evita “database not up to date”).  
2. `revision --autogenerate -m "...“` cuando cambien modelos.  
3. `upgrade head` para aplicar la nueva.

## Próximos pasos sugeridos
- Autenticación y hashing de password real.
- Autorización efectiva usando roles/permisos en los endpoints.
- Tests automáticos (FastAPI TestClient + DB temporal).
- Endpoints de bootstrap de roles/permissions.
- Nuevos canales (WhatsApp) y manejo multi-tenant avanzado.
