# Turnix – Sistema de Gestión de Citas para Negocios de Belleza

Sistema de agendamiento de citas para barberías, peluquerías y salones de belleza, con interacción vía Telegram Bot y panel administrativo web.

**Proyecto académico** – Electiva de profundización: Programación en Python  
Universidad – 2026

---

## Tecnologías

| Capa       | Tecnología                                      |
|------------|-------------------------------------------------|
| Backend    | Python 3.11+, FastAPI, SQLAlchemy, Pydantic     |
| Base de datos | SQLite (por defecto) / PostgreSQL (opcional) |
| Bot        | python-telegram-bot v21                         |
| Frontend   | React 18 + Vite 5                               |
| Servidor   | Uvicorn                                         |

---

## Estructura del proyecto

```
Boot_GRUP_EP_UPCSAM/
├── app/
│   ├── main.py                    # Punto de entrada FastAPI
│   ├── core/
│   │   ├── config.py              # Variables de entorno
│   │   └── database.py            # Conexión SQLAlchemy
│   ├── models/                    # Modelos ORM SQLAlchemy
│   │   ├── tenant.py              # Negocio
│   │   ├── service.py             # Servicio
│   │   ├── client.py              # Cliente (Telegram)
│   │   ├── appointment.py         # Cita
│   │   ├── conversation.py        # Conversación
│   │   └── message.py             # Mensaje
│   ├── schemas/                   # Pydantic: validación I/O
│   ├── repositories/              # CRUD de base de datos
│   ├── services/
│   │   └── availability_service.py # Lógica de disponibilidad
│   ├── api/v1/endpoints/          # Routers FastAPI
│   ├── database/
│   │   └── seed.py                # Datos de prueba
│   └── bot/
│       └── telegram_bot.py        # Bot de Telegram
├── frontend/                      # Panel web React + Vite
├── alembic/                       # Migraciones (opcional)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Requisitos previos

- Python 3.11 o superior
- Node.js 18 o superior (para el frontend)
- Git

---

## Instalación del backend

```bash
cd Boot_GRUP_EP_UPCSAM

python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

---

## Configuración del .env

```bash
copy .env.example .env
```

Edita el `.env`. Para SQLite local solo configura el token de Telegram:

```env
DATABASE_URL=sqlite:///./turnix.db
TELEGRAM_BOT_TOKEN=tu_token_aqui
```

---

## Ejecución del backend

```bash
uvicorn app.main:app --reload
```

- Backend: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- Health: http://localhost:8000/health

---

## Seed – Datos de prueba

```bash
python -m app.database.seed
```

Crea negocio demo, 4 servicios, 1 cliente y 1 cita de prueba.

---

## Bot de Telegram

1. Habla con @BotFather en Telegram → `/newbot` → copia el token
2. Pega el token en el `.env`: `TELEGRAM_BOT_TOKEN=tu_token`
3. Ejecuta:

```bash
python -m app.bot.telegram_bot
```

Flujo: `/start` → menú → Agendar cita → servicio → fecha → horario → confirmar

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Panel en: http://localhost:5173

Secciones: Dashboard, Servicios, Clientes, Citas, Conversaciones, Negocio.

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /health | Estado del backend |
| GET/POST | /api/v1/businesses/ | Negocios |
| GET/POST | /api/v1/services/ | Servicios |
| GET/POST | /api/v1/clients/ | Clientes |
| GET | /api/v1/clients/telegram/{id} | Cliente por Telegram ID |
| GET/POST | /api/v1/appointments/ | Citas |
| PATCH | /api/v1/appointments/{id}/cancel | Cancelar cita |
| PATCH | /api/v1/appointments/{id}/complete | Completar cita |
| GET | /api/v1/availability/?tenant_id=1&service_id=1&date=2026-05-10 | Horarios disponibles |
| GET | /api/v1/conversations/{id}/messages | Mensajes de conversación |

---

## Flujo de prueba completo

1. `uvicorn app.main:app --reload`
2. `python -m app.database.seed`
3. Abrir http://localhost:8000/docs
4. `cd frontend && npm run dev`
5. Abrir http://localhost:5173
6. `python -m app.bot.telegram_bot`
7. Escribir `/start` al bot en Telegram
8. Agendar una cita desde Telegram
9. Verificar la cita en el panel → Citas

---

## Errores comunes

| Error | Solución |
|-------|----------|
| TELEGRAM_BOT_TOKEN no definido | Configura el token en `.env` |
| ModuleNotFoundError | Activa venv y ejecuta `pip install -r requirements.txt` |
| Puerto 8000 ocupado | `uvicorn app.main:app --port 8001` |

---

## Estado del proyecto

- [x] Backend FastAPI funcional con SQLite y PostgreSQL
- [x] CRUD: negocios, servicios, clientes, citas
- [x] Validación de disponibilidad y cruces de horario
- [x] Bot de Telegram con flujo de agendamiento
- [x] Registro de conversaciones y mensajes
- [x] Frontend React+Vite con panel administrativo completo
- [x] Seed de datos de prueba
- [x] Swagger / OpenAPI disponible
