# 🚀 Radiar de Ventas Telegram

> Para leer este README cómodo: instala la extensión **Markdown Preview Enhanced** en VS Code (se recomienda automáticamente) y abre el preview con `Cmd/Ctrl+Shift+V`.

Backend SaaS multi‑tenant para rastrear y gestionar mensajes, servicios, canales y conversaciones en Telegram, listo para crecer a otros canales (p. ej. WhatsApp).

## 🧩 Stack
- FastAPI (API REST)
- SQLAlchemy (ORM)
- Alembic (migraciones)
- PostgreSQL (DB)
- Docker Compose (entorno)

## 🛠️ Requisitos
- Docker + Docker Compose
- Cliente SQL opcional (DBeaver)
- Opcional local: Python 3.11+ (el flujo recomendado es vía Docker)

## ⚡ Inicio rápido
1) Variables de entorno  
   `cp .env.example .env`  
   Ajusta `DATABASE_URL` usando `db` como host (la app vive en contenedor).

2) Construir / levantar contenedores  
   - Primera vez o cambio de deps: `docker compose up --build`  
   - Siguientes veces: `docker compose up`

3) Migraciones (orden correcto)  
   ```bash
   docker compose exec -e PYTHONPATH=/code app alembic -c /code/alembic.ini upgrade head          # aplica pendientes
   docker compose exec -e PYTHONPATH=/code app alembic -c /code/alembic.ini revision --autogenerate -m "feat: crear entidades MER"  # solo si cambias modelos
   docker compose exec -e PYTHONPATH=/code app alembic -c /code/alembic.ini upgrade head          # aplica la nueva
   ```
   Si tenías el error de base “no al día”, el primer `upgrade head` lo resuelve.

4) Comprobaciones útiles  
   - API docs: http://localhost:8000/docs (Swagger) / http://localhost:8000/redoc  
   - Logs app: `docker compose logs -f app`  
   - Logs DB: `docker compose logs -f db`  
   - Red interna: `docker network inspect radiar_de_ventas_telegram_rastreo_network` (el nombre puede variar según tu carpeta)

5) Reset completo (incluye volúmenes)  
   `docker compose down -v`

## 📂 Estructura
```
radiar_de_ventas_telegram
├─ Dockerfile
├─ README.md
├─ alembic/
│  ├─ env.py
│  ├─ script.py.mako
│  └─ versions/
├─ alembic.ini
├─ app/
│  ├─ api/v1/endpoints/...
│  ├─ core/
│  ├─ models/
│  ├─ repositories/
│  └─ schemas/
├─ docker-compose.yml
└─ requirements.txt
```

## 🔍 Flujo de desarrollo
1) Crear/ajustar modelo (`app/models/…`) e importarlo en `app/models/__init__.py` si aplica.  
2) Schemas (`app/schemas/…`).  
3) Repositorio (`app/repositories/…`).  
4) Endpoint (`app/api/v1/endpoints/…`) y registrar en `app/api/v1/api.py`.  
5) `revision --autogenerate` y `upgrade head`.  
6) Probar en Swagger / DB.

## 📌 Notas
- La app corre en :8000; Postgres en :5432.
- Código montado en `/code` dentro del contenedor; Alembic usa `/code/alembic.ini`.
- Volumen de datos: `postgres_data`.

## 📚 Más detalle
Consulta `tory.md` para la descripción de dominio, capas y próximos pasos.
