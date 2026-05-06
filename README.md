# Sistema de gestión de citas para negocios del sector de belleza

**Turnix** es un proyecto académico desarrollado para la asignatura **Electiva de profundización: Programación en Python**, de la **Universidad Piloto de Colombia – Seccional Alto Magdalena**, orientado a la construcción de una herramienta digital para apoyar la gestión de citas, servicios, clientes y conversaciones en negocios del sector de belleza y cuidado personal.

El proyecto fue desarrollado por:

- **Bryan Duván Gómez Bohórquez**
- **Joab Jazed Munevar González**
- **Juan Camilo Ibáñez Gaitán**

**Universidad Piloto de Colombia – Seccional Alto Magdalena**  
**Facultad de Ingeniería**  
**Electiva de profundización: Programación en Python**  
**Docente:** Ing. Emmanuel Rivera Guzmán  
**Año:** 2026

---

## Descripción del proyecto

**Turnix** es una aplicación web orientada a negocios del sector de belleza, como barberías, peluquerías, salones de belleza y establecimientos de cuidado personal, que requieren organizar de forma más clara sus servicios, clientes, horarios y procesos de agendamiento.

El sistema permite administrar negocios, registrar servicios, gestionar clientes, crear y consultar citas, validar disponibilidad de horarios y almacenar conversaciones asociadas a la atención. Además, integra un bot de Telegram que facilita la interacción con los clientes mediante un flujo conversacional para consultar servicios y realizar procesos de agendamiento.

La solución está compuesta por un backend desarrollado con **FastAPI**, una base de datos relacional gestionada con **SQLAlchemy**, un panel administrativo construido con **React y Vite**, y un bot conectado a la **API de Telegram**.

---

## Objetivo del proyecto

Desarrollar un sistema funcional de gestión de citas para negocios del sector de belleza, integrando una API REST, una base de datos relacional, un panel administrativo web y un bot de Telegram, con el propósito de aplicar conocimientos de programación en Python, arquitectura en capas, diseño de APIs, validación de datos, manejo de bases de datos y construcción de interfaces web.

---

## Alcance del sistema

Turnix busca responder a una problemática frecuente en negocios del sector de belleza: la gestión informal de citas mediante agendas físicas, mensajes dispersos, llamadas o registros manuales.

El sistema permite centralizar la información y facilitar la administración de los procesos principales del negocio. Dentro de su alcance se contempla:

- Registro y administración de negocios.
- Gestión de servicios ofrecidos por cada negocio.
- Registro y consulta de clientes.
- Creación, consulta, actualización y cancelación de citas.
- Validación de disponibilidad de horarios.
- Detección de cruces en la agenda.
- Consulta de conversaciones y mensajes asociados al proceso de atención.
- Interacción mediante bot de Telegram.
- Visualización de información desde un panel administrativo web.
- Documentación automática de la API mediante Swagger/OpenAPI.

---

## Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Pydantic |
| Base de datos | SQLite para desarrollo local y PostgreSQL como alternativa para producción |
| Frontend | React 18, Vite 5 |
| Bot conversacional | python-telegram-bot |
| Servidor de desarrollo | Uvicorn |
| Documentación de API | Swagger / OpenAPI |

---

## Arquitectura general

El proyecto sigue una estructura organizada por capas, separando responsabilidades entre configuración, modelos, esquemas, repositorios, servicios, endpoints, base de datos, frontend y bot de Telegram.

```text
Boot_GRUP_EP_UPCSAM/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   └── availability_service.py
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   ├── database/
│   │   └── seed.py
│   └── bot/
│       └── telegram_bot.py
├── frontend/
│   ├── src/
│   │   ├── api.js
│   │   └── pages/
│   └── .env.example
├── alembic/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Funcionalidades principales

- Gestión de negocios del sector de belleza.
- Registro y administración de servicios.
- Registro y consulta de clientes.
- Creación, consulta, actualización y cancelación de citas.
- Validación de disponibilidad de horarios.
- Detección de cruces de citas.
- Consulta de conversaciones y mensajes.
- Bot de Telegram para interacción con clientes.
- Panel administrativo web.
- Documentación automática de endpoints mediante Swagger/OpenAPI.
- Compatibilidad con SQLite para desarrollo local.
- Compatibilidad opcional con PostgreSQL para entornos de producción.

---

## Instalación del backend

Desde la raíz del proyecto, crea un entorno virtual:

```bash
python -m venv venv
```

Activa el entorno virtual.

En Windows:

```bash
venv\Scripts\activate
```

En Linux o macOS:

```bash
source venv/bin/activate
```

Instala las dependencias del backend:

```bash
pip install -r requirements.txt
```

El entorno virtual debe permanecer activo para ejecutar comandos relacionados con el backend.

---

## Instalación del frontend

Ingresa a la carpeta del frontend:

```bash
cd frontend
```

Instala las dependencias:

```bash
npm install
```

---

## Configuración de variables de entorno

### Backend

Desde la raíz del proyecto, copia el archivo de ejemplo.

En Windows:

```bash
copy .env.example .env
```

En Linux o macOS:

```bash
cp .env.example .env
```

Variables principales para desarrollo local:

```env
DATABASE_URL=sqlite:///./turnix.db
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
FRONTEND_URL=frontend_en_desarrollo_local
```

Para un entorno con PostgreSQL, se debe configurar la variable `DATABASE_URL` con la cadena de conexión correspondiente.

No se deben incluir tokens reales, contraseñas ni credenciales sensibles dentro del repositorio.

### Frontend

Desde la carpeta `frontend`, copia el archivo de ejemplo:

```bash
copy .env.example .env
```

Variable principal:

```env
VITE_API_URL=api_backend_en_desarrollo_local
```

Esta variable permite que el frontend consuma los endpoints del backend.

---

## Ejecución local

### Backend

Desde la raíz del proyecto, con el entorno virtual activo, ejecuta:

```bash
uvicorn app.main:app --reload
```

El backend se ejecuta en el puerto **8000**.

La documentación interactiva de la API queda disponible en la ruta `/docs` del servidor backend activo.

### Frontend

Desde la carpeta `frontend`, ejecuta:

```bash
npm run dev
```

El panel administrativo se ejecuta en el puerto **5173**.

---

## Bot de Telegram

El sistema incluye un bot de Telegram para permitir la interacción conversacional con los clientes.

Para configurarlo:

1. Abre Telegram.
2. Busca el bot oficial **BotFather**.
3. Crea un nuevo bot con el comando `/newbot`.
4. Copia el token generado.
5. Agrega el token en el archivo `.env` del backend.

```env
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
```

Para iniciar el bot:

```bash
python -m app.bot.telegram_bot
```

Flujo general del bot:

```text
/start
Seleccionar servicio
Elegir fecha
Elegir horario disponible
Confirmar cita
```

---

## Datos de prueba

El proyecto incluye un script para cargar datos iniciales de demostración.

Desde la raíz del proyecto, ejecuta:

```bash
python -m app.database.seed
```

Este comando permite crear información base para probar el sistema, como un negocio de demostración, servicios, clientes y citas iniciales.

---

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Verifica el estado del backend |
| GET / POST | `/api/v1/businesses/` | Gestión de negocios |
| GET / POST | `/api/v1/services/` | Gestión de servicios |
| GET | `/api/v1/services/?tenant_id=1` | Consulta de servicios por negocio |
| GET / POST | `/api/v1/clients/` | Gestión de clientes |
| GET / POST | `/api/v1/appointments/` | Gestión de citas |
| PATCH | `/api/v1/appointments/{id}/cancel` | Cancelación de citas |
| PATCH | `/api/v1/appointments/{id}/complete` | Marcado de citas como completadas |
| GET | `/api/v1/availability/` | Consulta de horarios disponibles |
| GET | `/api/v1/conversations/` | Consulta de conversaciones |
| GET | `/api/v1/conversations/{id}/messages` | Consulta de mensajes por conversación |

La documentación completa de la API se encuentra en la ruta `/docs` del backend activo.

---

## Pruebas recomendadas

Para verificar el funcionamiento general del sistema, se recomienda ejecutar los siguientes comandos.

### Backend

```bash
pip install -r requirements.txt
python -m compileall app
python -m app.database.seed
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run build
npm run dev
```

### Bot de Telegram

```bash
python -m app.bot.telegram_bot
```

---

## Despliegue

| Componente | Estado |
|---|---|
| Backend | Pendiente de despliegue |
| Frontend | Pendiente de despliegue |
| Bot de Telegram | Pendiente de despliegue |
| Documentación de API | Pendiente de despliegue |

El despliegue en producción puede realizarse posteriormente mediante servicios como Render, Railway, Vercel u otras plataformas compatibles con aplicaciones Python y frontend web.

---

## Estado actual del proyecto

- [x] Backend desarrollado con FastAPI.
- [x] Estructura organizada por capas.
- [x] Modelos y esquemas principales implementados.
- [x] Gestión de negocios, servicios, clientes y citas.
- [x] Validación de disponibilidad y cruces de horario.
- [x] Script de datos de prueba.
- [x] Documentación automática de la API con Swagger/OpenAPI.
- [x] Frontend desarrollado con React y Vite.
- [x] Panel administrativo funcional para demostración.
- [ ] Bot de Telegram pendiente de validación completa con token real.
- [ ] Despliegue en entorno de producción pendiente.

---

## Contexto académico

Este proyecto fue desarrollado como parte del proceso formativo de la asignatura **Electiva de profundización: Programación en Python**, con el propósito de aplicar conocimientos de programación, desarrollo backend, integración de APIs, bases de datos, arquitectura de software y construcción de interfaces web.

La propuesta responde a una problemática identificada en negocios del sector de belleza, donde la gestión de citas suele realizarse de manera manual o informal, generando dificultades en la organización de horarios, servicios, clientes y conversaciones.

---

## Autores

**Bryan Duván Gómez Bohórquez**  
**Joab Jazed Munevar González**  
**Juan Camilo Ibáñez Gaitán**

Universidad Piloto de Colombia – Seccional Alto Magdalena  
Facultad de Ingeniería  
Electiva de profundización: Programación en Python  
2026