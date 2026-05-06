# Sistema de gestión de citas para negocios del sector de belleza

**Turnix** es un proyecto académico desarrollado para la asignatura **Electiva de profundización: Programación en Python**, de la **Universidad Piloto de Colombia**, orientado a la construcción de una herramienta digital para la gestión de citas en negocios del sector de belleza y cuidado personal.

El proyecto fue desarrollado por:

- **Bryan Duván Gómez Bohórquez**
- **Joab Jazed Munevar González**
- **Juan Camilo Ibáñez Gaitán**

**Universidad Piloto de Colombia**  
**Facultad de Ingeniería**  
**Electiva de profundización: Programación en Python**  
**Año:** 2026

---

## Descripción del proyecto

**Turnix** es una aplicación web diseñada para apoyar la gestión de citas en negocios del sector de belleza, como barberías, peluquerías, salones de belleza y establecimientos de cuidado personal.

El sistema permite registrar negocios, servicios, clientes y citas, consultar disponibilidad de horarios y llevar un historial de conversaciones asociadas al proceso de atención. Además, integra un bot de Telegram que permite a los clientes interactuar con el sistema de forma conversacional para consultar servicios y realizar procesos de agendamiento.

La solución está compuesta por un backend desarrollado con **FastAPI**, un panel administrativo construido con **React y Vite**, una base de datos relacional gestionada mediante **SQLAlchemy** y un bot conectado a la **API de Telegram**.

---

## Objetivo del proyecto

Desarrollar un sistema funcional de gestión de citas que integre una API REST, un panel administrativo web y un bot de Telegram, aplicando conceptos de programación en Python, arquitectura en capas, manejo de bases de datos relacionales, validación de datos, consumo de servicios y diseño de interfaces para la administración de información.

---

## Alcance del sistema

El sistema está orientado a resolver una necesidad común en negocios del sector de belleza: la gestión informal de citas, servicios y conversaciones mediante agendas físicas, mensajes dispersos o registros manuales.

Turnix busca centralizar esta información en una plataforma digital que permita:

- Registrar y administrar negocios.
- Gestionar servicios ofrecidos por cada negocio.
- Registrar clientes.
- Crear, consultar, actualizar y cancelar citas.
- Validar disponibilidad de horarios.
- Evitar cruces de citas.
- Consultar conversaciones y mensajes asociados al proceso de atención.
- Permitir agendamiento mediante un bot de Telegram.
- Visualizar información desde un panel administrativo web.

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

El proyecto sigue una estructura organizada por capas, separando responsabilidades entre modelos, esquemas, repositorios, servicios, endpoints, configuración del sistema, frontend y bot de Telegram.

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
