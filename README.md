# Sistema de gestión de citas para negocios del sector de belleza

**Proyecto académico** — Electiva de profundización: Programación en Python  
Universidad — 2026

---

## Descripción del proyecto

Turnix es una aplicación web para la gestión de citas en negocios del sector de belleza, como barberías, peluquerías y salones. Permite registrar negocios, servicios, clientes y citas, consultar la disponibilidad de horarios y llevar un historial de conversaciones iniciadas a través de un bot de Telegram.

El sistema está compuesto por un backend desarrollado con FastAPI, un panel administrativo web construido con React y Vite, y un bot de Telegram que permite a los clientes agendar citas de forma conversacional.

---

## Objetivo

Desarrollar un sistema funcional de gestión de citas que integre una API REST, un panel de administración web y un bot de Telegram, aplicando los conceptos de programación orientada a objetos, diseño de APIs, manejo de bases de datos relacionales y arquitectura en capas.

---

## Tecnologías utilizadas

| Capa          | Tecnología                                        |
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
│   ├── main.py                     # Punto de entrada de la aplicación FastAPI
│   ├── core/
│   │   ├── config.py               # Carga de variables de entorno
│   │   └── database.py             # Configuración de la conexión a la base de datos
│   ├── models/                     # Modelos ORM con SQLAlchemy
│   │   ├── tenant.py               # Negocio
│   │   ├── service.py              # Servicio ofrecido
│   │   ├── client.py               # Cliente registrado desde Telegram
│   │   ├── appointment.py          # Cita agendada
│   │   ├── conversation.py         # Conversación del bot
│   │   └── message.py              # Mensaje individual
│   ├── schemas/                    # Esquemas Pydantic para validación de entrada y salida
│   ├── repositories/               # Acceso a base de datos (operaciones CRUD)
│   ├── services/
│   │   └── availability_service.py # Lógica de validación de disponibilidad
│   ├── api/v1/endpoints/           # Routers de la API REST
│   ├── database/
│   │   └── seed.py                 # Script para cargar datos de prueba
│   └── bot/
│       └── telegram_bot.py         # Implementación del bot de Telegram
├── frontend/                       # Panel administrativo web (React + Vite)
│   ├── src/
│   │   ├── api.js                  # Cliente HTTP hacia la API
│   │   ├── pages/                  # Vistas del panel
│   │   └── ...
│   └── .env.example                # Variables de entorno del frontend
├── alembic/                        # Migraciones de base de datos (opcional)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Funcionalidades principales

- Registro y gestión de negocios, servicios y clientes.
- Agendamiento de citas con validación de disponibilidad y detección de cruces de horario.
- Bot de Telegram con flujo conversacional para que los clientes agenden citas.
- Historial de conversaciones y mensajes del bot.
- Panel administrativo web con vistas de dashboard, servicios, clientes, citas y conversaciones.
- Documentación automática de la API mediante Swagger/OpenAPI.
- Compatibilidad con SQLite para desarrollo local y PostgreSQL para entornos de producción.

---

## Instalación del backend

```bash
# Desde la raíz del proyecto
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

---

## Instalación del frontend

```bash
cd frontend
npm install
```

---

## Configuración de variables de entorno

### Backend

Copia el archivo de ejemplo y edítalo con los valores correspondientes:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Variables requeridas para ejecución con SQLite:

```env
DATABASE_URL=sqlite:///./turnix.db
TELEGRAM_BOT_TOKEN=tu_token_aqui
FRONTEND_URL=http://localhost:5173
```

Para usar PostgreSQL, descomenta y completa las variables `POSTGRES_*` en el `.env`.

### Frontend

```bash
cd frontend
copy .env.example .env
```

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## Ejecución local

### Backend

```bash
uvicorn app.main:app --reload
```

El backend queda disponible en el puerto 8000. La documentación interactiva de la API se puede consultar en la ruta `/docs` mientras el servidor esté activo.

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

Flujo de agendamiento desde Telegram: `/start` → seleccionar servicio → elegir fecha → elegir horario → confirmar cita.

---

## Datos de prueba

Para cargar un conjunto inicial de datos en la base de datos:

```bash
python -m app.database.seed
```

Este script crea un negocio de demostración, cuatro servicios, un cliente y una cita de prueba.

---

## Endpoints principales

| Método   | Ruta                                                        | Descripción                        |
|----------|-------------------------------------------------------------|------------------------------------|
| GET      | /health                                                     | Estado del backend                 |
| GET/POST | /api/v1/businesses/                                         | Gestión de negocios                |
| GET/POST | /api/v1/services/                                           | Gestión de servicios               |
| GET/POST | /api/v1/clients/                                            | Gestión de clientes                |
| GET      | /api/v1/clients/telegram/{telegram_id}                      | Consultar cliente por Telegram ID  |
| GET/POST | /api/v1/appointments/                                       | Gestión de citas                   |
| PATCH    | /api/v1/appointments/{id}/cancel                            | Cancelar una cita                  |
| PATCH    | /api/v1/appointments/{id}/complete                          | Completar una cita                 |
| GET      | /api/v1/availability/?tenant_id=1&service_id=1&date=FECHA   | Consultar horarios disponibles     |
| GET      | /api/v1/conversations/{id}/messages                         | Mensajes de una conversación       |

La documentación completa con esquemas de entrada y salida está disponible en la ruta `/docs` del backend.

---

## Despliegue en línea

| Componente           | Estado                      |
|----------------------|-----------------------------|
| Estado general       | Pendiente de despliegue     |
| Frontend             | Pendiente de despliegue     |
| Backend              | Pendiente de despliegue     |
| Documentación de la API | Pendiente de despliegue  |

---

## Estado del proyecto

- [x] Backend funcional con SQLite y compatibilidad con PostgreSQL
- [x] CRUD completo: negocios, servicios, clientes, citas
- [x] Validación de disponibilidad y detección de cruces de horario
- [x] Bot de Telegram con flujo de agendamiento
- [x] Registro de conversaciones y mensajes
- [x] Panel administrativo con React y Vite
- [x] Script de datos de prueba (seed)
- [x] Documentación de la API con Swagger/OpenAPI

---

## Autores

Proyecto desarrollado como parte de la electiva de profundización en Programación en Python — Universidad, 2026.
