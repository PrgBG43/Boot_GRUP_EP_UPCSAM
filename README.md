# Sistema de gestion de citas para negocios del sector de belleza

**Proyecto academico** — Electiva de profundizacion: Programacion en Python
Universidad — 2026

---

## Descripcion del proyecto

Turnix es una aplicacion web para la gestion de citas en negocios del sector de
belleza (barberias, peluquerias, salones). Permite registrar negocios, servicios,
clientes y citas, consultar la disponibilidad de horarios y llevar un historial
de conversaciones iniciadas a traves de un bot de Telegram.

El sistema esta compuesto por un backend desarrollado con FastAPI, un panel
administrativo web construido con React y Vite, y un bot de Telegram que permite
a los clientes agendar citas de forma conversacional.

---

## Objetivo

Desarrollar un sistema funcional de gestion de citas que integre una API REST,
un panel de administracion web y un bot de Telegram, aplicando conceptos de
programacion orientada a objetos, diseno de APIs, manejo de bases de datos
relacionales y arquitectura en capas.

---

## Tecnologias utilizadas

| Capa          | Tecnologia                                        |
|---------------|---------------------------------------------------|
| Backend       | Python 3.11+, FastAPI, SQLAlchemy, Pydantic       |
| Base de datos | SQLite (por defecto) / PostgreSQL (opcional)      |
| Bot           | python-telegram-bot v21                           |
| Frontend      | React 18, Vite 5                                  |
| Servidor      | Uvicorn                                           |

---

## Estructura del repositorio

```
Boot_GRUP_EP_UPCSAM/
├── app/
│   ├── main.py                     # Punto de entrada FastAPI
│   ├── core/
│   │   ├── config.py               # Variables de entorno
│   │   └── database.py             # Motor y sesion de base de datos
│   ├── models/                     # Modelos ORM SQLAlchemy
│   ├── schemas/                    # Esquemas Pydantic
│   ├── repositories/               # Operaciones CRUD
│   ├── services/
│   │   └── availability_service.py # Logica de disponibilidad
│   ├── api/v1/endpoints/           # Routers de la API REST
│   ├── database/
│   │   └── seed.py                 # Datos de prueba
│   └── bot/
│       └── telegram_bot.py         # Bot de Telegram
├── frontend/                       # Panel administrativo (React + Vite)
│   ├── src/
│   │   ├── api.js                  # Cliente HTTP hacia la API
│   │   └── pages/                  # Vistas del panel
│   └── .env.example
├── alembic/                        # Migraciones de base de datos
├── requirements.txt
├── .env.example
└── README.md
```

---

## Funcionalidades principales

- Registro y gestion de negocios, servicios y clientes.
- Agendamiento de citas con validacion de disponibilidad y deteccion de cruces.
- Bot de Telegram con flujo conversacional para agendar citas.
- Historial de conversaciones y mensajes del bot.
- Panel administrativo con vistas de dashboard, servicios, clientes, citas y conversaciones.
- Documentacion automatica de la API con Swagger/OpenAPI.
- Compatibilidad con SQLite (desarrollo) y PostgreSQL (produccion).

---

## Instalacion del backend

```bash
# Desde la raiz del proyecto
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

> El entorno virtual debe estar activo antes de ejecutar cualquier comando.

---

## Instalacion del frontend

```bash
cd frontend
npm install
```

---

## Configuracion de variables de entorno

### Backend

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Variables requeridas para SQLite:

```env
DATABASE_URL=sqlite:///./turnix.db
TELEGRAM_BOT_TOKEN=tu_token_aqui
FRONTEND_URL=http://localhost:5173
```

Para PostgreSQL, completa las variables `POSTGRES_*` en el `.env`.

### Frontend

```bash
cd frontend
copy .env.example .env
```

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## Ejecucion local

### Backend

```bash
uvicorn app.main:app --reload
```

El backend queda disponible en el puerto 8000.
La documentacion interactiva de la API esta en la ruta `/docs` del servidor.

### Frontend

```bash
cd frontend
npm run dev
```

El panel administrativo se ejecuta en el puerto 5173.

---

## Bot de Telegram

1. Abre Telegram y busca **@BotFather**.
2. Ejecuta `/newbot` y sigue las instrucciones para obtener el token.
3. Copia el token en el archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
```

4. Inicia el bot:

```bash
python -m app.bot.telegram_bot
```

Flujo desde Telegram: `/start` -> seleccionar servicio -> elegir fecha -> elegir horario -> confirmar cita.

---

## Datos de prueba

```bash
python -m app.database.seed
```

Crea un negocio de demostracion, cuatro servicios, un cliente y una cita de prueba.

---

## Endpoints principales

| Metodo   | Ruta                                                        | Descripcion                        |
|----------|-------------------------------------------------------------|------------------------------------|
| GET      | /health                                                     | Estado del backend                 |
| GET/POST | /api/v1/businesses/                                         | Gestion de negocios                |
| GET/POST | /api/v1/services/                                           | Gestion de servicios               |
| GET      | /api/v1/services/?tenant_id=1                               | Servicios filtrados por negocio    |
| GET/POST | /api/v1/clients/                                            | Gestion de clientes                |
| GET/POST | /api/v1/appointments/                                       | Gestion de citas                   |
| PATCH    | /api/v1/appointments/{id}/cancel                            | Cancelar una cita                  |
| PATCH    | /api/v1/appointments/{id}/complete                          | Completar una cita                 |
| GET      | /api/v1/availability/                                       | Horarios disponibles               |
| GET      | /api/v1/conversations/                                      | Listado de conversaciones          |
| GET      | /api/v1/conversations/{id}/messages                         | Mensajes de una conversacion       |

La documentacion completa esta disponible en la ruta `/docs` del backend activo.

---

## Despliegue

| Componente  | Estado                  |
|-------------|-------------------------|
| Backend     | Pendiente de despliegue |
| Frontend    | Pendiente de despliegue |
| Bot         | Pendiente de despliegue |
| API docs    | Pendiente de despliegue |

---

## Estado del proyecto

- [x] Backend funcional con SQLite y compatibilidad con PostgreSQL
- [x] CRUD completo: negocios, servicios, clientes, citas
- [x] Validacion de disponibilidad y deteccion de cruces de horario
- [x] Script de datos de prueba (seed) ejecutado y verificado
- [x] Documentacion de la API con Swagger/OpenAPI
- [x] Frontend (React + Vite) — codigo correcto, compilacion pendiente de verificar en entorno con Node.js
- [ ] Bot de Telegram — inicio verificado, flujo conversacional completo pendiente de prueba con token real
- [ ] Despliegue en entorno de produccion

---

## Autores

Proyecto desarrollado como parte de la electiva de profundizacion en Programacion en Python — Universidad, 2026.
