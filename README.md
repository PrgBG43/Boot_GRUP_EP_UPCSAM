# Turnix — Plataforma SaaS multi-tenant de gestión de citas

**Turnix** es una plataforma SaaS multi-tenant para la gestión de citas en negocios del sector de belleza y cuidado personal (barberías, peluquerías, salones de belleza). Permite que múltiples negocios operen de forma aislada bajo la misma plataforma, con autenticación JWT, roles de usuario y planes freemium.

Desarrollado como proyecto académico para la asignatura **Electiva de profundización: Programación en Python** — **Universidad Piloto de Colombia, 2026**.

**Autores:**
- Bryan Duván Gómez Bohórquez
- Joab Jazed Munevar González
- Juan Camilo Ibáñez Gaitán

---

## Características principales

- **Multi-tenant**: cada negocio tiene sus propios datos aislados (clientes, citas, servicios)
- **Autenticación JWT**: tokens con expiración de 8 horas
- **4 roles**: `superadmin`, `tenant_admin`, `staff`, `customer`
- **Planes freemium**: Gratuito / Premium / Empresarial con límites configurables
- **Dashboard de métricas**: global (superadmin) y por negocio (con gráfica de 7 días)
- **Bot de Telegram**: flujo conversacional para agendar citas
- **Frontend React**: panel administrativo con navegación basada en rol

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, FastAPI 0.135, SQLAlchemy 2.0 |
| Auth | python-jose (JWT), passlib + bcrypt 4.0.1 |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Frontend | React 18, Vite 5, Recharts |
| Bot | python-telegram-bot 21.6 |
| Config | pydantic-settings, .env |

---

## Arquitectura

```text
Boot_GRUP_EP_UPCSAM/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py          # Settings (.env)
│   │   ├── database.py        # SQLAlchemy engine
│   │   ├── security.py        # hash_password, JWT
│   │   └── auth.py            # FastAPI dependencies (roles)
│   ├── models/                # SQLAlchemy ORM
│   ├── schemas/               # Pydantic
│   ├── repositories/          # DB queries
│   ├── services/
│   │   └── availability_service.py
│   ├── api/v1/endpoints/      # REST endpoints
│   ├── database/seed.py       # Demo data
│   └── bot/telegram_bot.py
├── frontend/
│   ├── src/
│   │   ├── context/AuthContext.jsx
│   │   ├── components/ProtectedRoute.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx  # Recharts + métricas reales
│   │   │   └── admin/Tenants.jsx
│   │   └── api.js             # Bearer token automático
│   └── package.json
├── requirements.txt
└── README.md
```

---

## Instalación y ejecución

### Backend

```bash
# Clonar y entrar al proyecto
git clone https://github.com/PrgBG43/Boot_GRUP_EP_UPCSAM.git
cd Boot_GRUP_EP_UPCSAM

# Crear entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Cargar datos de demostración
python -m app.database.seed

# Iniciar servidor (http://localhost:8000)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

### Variables de entorno opcionales

Crear `.env` en la raíz del proyecto:

```env
DATABASE_URL=sqlite:///./turnix.db
SECRET_KEY=cambia-esto-en-produccion
TELEGRAM_TOKEN=tu_token_aqui
```

---

## Credenciales demo

Ejecuta `python -m app.database.seed` para crear los datos de demostración.

| Rol | Email | Contraseña |
|---|---|---|
| Superadmin | `admin@turnix.demo` | `Admin123*` |
| Administrador de negocio | `negocio@turnix.demo` | `Negocio123*` |
| Personal / Staff | `staff@turnix.demo` | `Staff123*` |

**Negocio demo:** Barbería Demo Turnix · slug: `barberia-demo` · plan: Premium

---

## Endpoints principales

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/login` | Login con email/password → JWT |
| GET | `/api/v1/auth/me` | Datos del usuario autenticado |

### Dashboard
| Método | Ruta | Rol requerido |
|---|---|---|
| GET | `/api/v1/dashboard/superadmin` | superadmin |
| GET | `/api/v1/dashboard/tenant` | tenant_admin, staff |

### Recursos
| Recurso | Ruta base |
|---|---|
| Negocios | `/api/v1/businesses/` |
| Servicios | `/api/v1/services/` |
| Clientes | `/api/v1/clients/` |
| Citas | `/api/v1/appointments/` |
| Planes | `/api/v1/plans/` |
| Disponibilidad | `/api/v1/availability/` |

Documentación interactiva disponible en `http://localhost:8000/docs`

---

## Roles y permisos

| Acción | superadmin | tenant_admin | staff | customer |
|---|:---:|:---:|:---:|:---:|
| Gestionar todos los negocios | ✅ | ❌ | ❌ | ❌ |
| Ver métricas globales | ✅ | ❌ | ❌ | ❌ |
| Gestionar su negocio | ✅ | ✅ | ❌ | ❌ |
| Gestionar servicios | ✅ | ✅ | ❌ | ❌ |
| Ver citas y clientes | ✅ | ✅ | ✅ | ❌ |
| Crear cita propia | ✅ | ✅ | ✅ | ✅ |

---

## Planes freemium

| Plan | Citas/mes | Servicios | Personal |
|---|---|---|---|
| Gratuito | 30 | 5 | 1 |
| Premium | 200 | 20 | 5 |
| Empresarial | Ilimitado | Ilimitado | Ilimitado |

---

## Bot de Telegram

El bot permite a los clientes agendar citas mediante conversación. Comandos:

- `/start` — Iniciar conversación
- `/servicios` — Ver servicios disponibles
- `/agendar` — Iniciar flujo de agendamiento
- `/miscitas` — Ver citas activas
- `/cancelar` — Cancelar cita

---

## Universidad Piloto de Colombia

**Asignatura:** Electiva de profundización: Programación en Python  
**Facultad:** Ingeniería  
**Año:** 2026

