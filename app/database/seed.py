# -*- coding: utf-8 -*-
"""
Seed profesional de Turnix.

Carga datos base versionados y crea el superadmin inicial desde variables de entorno.
Los datos demo solo se crean cuando TURNIX_DEMO_SEED=true.

Uso:
  python -m app.database.seed
"""
import os
import re
import sys
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.schema_migrations import ensure_schema_compatibility
from app.core.security import hash_password
from app.core.slug import ensure_unique_slug

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw")


def _read_sql(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_state_sql(path: str):
    text = _read_sql(path)
    rows = re.findall(r"\((\d+),\s*'([^']+)',\s*'([^']+)'\)", text)
    return [{"id": int(i), "code": code, "description": desc} for i, code, desc in rows]


def _parse_city_sql(path: str):
    text = _read_sql(path)
    rows = re.findall(r"\((\d+),\s*'([^']+)',\s*'([^']+)',\s*(\d+)\)", text)
    return [
        {"id": int(i), "code": code, "description": desc, "state_id": int(state_id)}
        for i, code, desc, state_id in rows
    ]


def _get_or_create(db, Model, filter_kwargs, create_kwargs=None):
    obj = db.query(Model).filter_by(**filter_kwargs).first()
    if obj:
        return obj, False
    payload = {**filter_kwargs, **(create_kwargs or {})}
    obj = Model(**payload)
    db.add(obj)
    db.flush()
    return obj, True


def _warn_missing_env():
    expected = [
        "TURNIX_SUPERADMIN_EMAIL",
        "TURNIX_SUPERADMIN_PASSWORD",
        "TURNIX_SUPERADMIN_FIRST_NAME",
        "TURNIX_SUPERADMIN_LAST_NAME",
        "TURNIX_DEMO_SEED",
    ]
    missing = [name for name in expected if os.getenv(name) is None]
    if missing:
        print("ADVERTENCIA: faltan variables de entorno para el seed inicial:")
        for name in missing:
            print(f"  - {name}")
        print("Se usarán valores de desarrollo definidos en app/core/config.py. Cámbialos antes de producción.")
    if settings.is_default_secret_key:
        print("ADVERTENCIA: SECRET_KEY usa el valor de desarrollo. Configura uno propio en producción.")


def _seed_plans(db):
    from app.models.plan import Plan
    from app.models.tenant import Tenant

    plans = [
        (
            "free",
            {
                "display_name": "Gratuito",
                "max_appointments_monthly": 50,
                "max_active_services": None,
                "max_staff": 3,
                "allows_advanced_reminders": False,
                "allows_analytics": False,
                "is_active": True,
            },
        ),
        (
            "premium",
            {
                "display_name": "Premium",
                "max_appointments_monthly": None,
                "max_active_services": None,
                "max_staff": None,
                "allows_advanced_reminders": True,
                "allows_analytics": True,
                "is_active": True,
            },
        ),
    ]
    result = {}
    for name, data in plans:
        plan, _ = _get_or_create(db, Plan, {"name": name}, data)
        for key, value in data.items():
            setattr(plan, key, value)
        result[name] = plan

    enterprise = db.query(Plan).filter(Plan.name == "enterprise").first()
    if enterprise:
        db.query(Tenant).filter(Tenant.plan_id == enterprise.id).update({"plan_id": result["premium"].id})
        enterprise.is_active = False
        enterprise.display_name = "Premium"
        enterprise.max_appointments_monthly = None
        enterprise.max_active_services = None
        enterprise.max_staff = None
        enterprise.allows_advanced_reminders = True
        enterprise.allows_analytics = True
    db.commit()
    return result


def _seed_roles(db):
    from app.models.user import Role

    roles_data = [
        ("superadmin", "Superadministrador de la plataforma Turnix"),
        ("tenant_admin", "Administrador de un negocio"),
        ("staff", "Personal del negocio"),
        ("customer", "Cliente final"),
    ]
    roles = {}
    for name, description in roles_data:
        role, _ = _get_or_create(db, Role, {"name": name}, {"description": description})
        role.description = description
        roles[name] = role
    db.commit()
    return roles


def _seed_locations(db):
    from app.models.location import City, State

    states_data = _parse_state_sql(os.path.join(RAW_DIR, "state.sql"))
    for item in states_data:
        state = db.query(State).filter(State.id == item["id"]).first()
        if not state:
            state = State(id=item["id"])
            db.add(state)
        state.code = item["code"]
        state.description = item["description"]
    db.commit()

    cities_data = _parse_city_sql(os.path.join(RAW_DIR, "city.sql"))
    for item in cities_data:
        city = db.query(City).filter(City.id == item["id"]).first()
        if not city:
            city = City(id=item["id"])
            db.add(city)
        city.code = item["code"]
        city.description = item["description"]
        city.state_id = item["state_id"]
    db.commit()

    cundinamarca = db.query(State).filter(State.id == 11).first()
    girardot = db.query(City).filter(City.id == 494).first()
    if not cundinamarca or cundinamarca.description != "CUNDINAMARCA":
        raise RuntimeError("El seed de departamentos no dejó CUNDINAMARCA con id 11.")
    if not girardot or girardot.code != "25307" or girardot.state_id != 11:
        raise RuntimeError("El seed de ciudades no dejó GIRARDOT con id 494, code 25307 y state_id 11.")

    return {
        "total_states": db.query(State).count(),
        "total_cities": db.query(City).count(),
        "cundinamarca": cundinamarca,
        "girardot": girardot,
    }


def _seed_superadmin(db, roles):
    from app.models.person import Person
    from app.models.user import User

    email = settings.TURNIX_SUPERADMIN_EMAIL.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        person = Person(
            first_name=settings.TURNIX_SUPERADMIN_FIRST_NAME.strip(),
            last_name=settings.TURNIX_SUPERADMIN_LAST_NAME.strip(),
        )
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            tenant_id=None,
            email=email,
            password_hash=hash_password(settings.TURNIX_SUPERADMIN_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.tenant_id = None
        user.is_active = True
        user.password_hash = hash_password(settings.TURNIX_SUPERADMIN_PASSWORD)
        if user.person:
            user.person.first_name = settings.TURNIX_SUPERADMIN_FIRST_NAME.strip()
            user.person.last_name = settings.TURNIX_SUPERADMIN_LAST_NAME.strip()

    user.roles = [roles["superadmin"]]
    db.commit()
    db.refresh(user)
    return user


def _create_demo_data(db, plans, roles, locations):
    from app.models.appointment import Appointment
    from app.models.client import Client
    from app.models.person import Person
    from app.models.service import Service
    from app.models.telegram_config import TelegramConfig
    from app.models.tenant import Tenant
    from app.models.user import User

    cundinamarca = locations["cundinamarca"]
    girardot = locations["girardot"]

    tenant = db.query(Tenant).filter(Tenant.slug.in_(["barberia-centro-turnix", "barberia-demo"])).first()
    if not tenant:
        tenant = Tenant(
            name="Barberia Centro Turnix",
            description="Negocio de prueba para desarrollo local.",
            phone="3001234567",
            address="Carrera 10 # 15-20, Girardot",
            city=girardot.description,
            state_id=cundinamarca.id,
            city_id=girardot.id,
            slug=ensure_unique_slug(db, "barberia-centro-turnix"),
            opening_time="08:00",
            closing_time="20:00",
            plan_id=plans["premium"].id,
            is_active=True,
        )
        db.add(tenant)
        db.flush()
    else:
        tenant.name = "Barberia Centro Turnix"
        tenant.description = "Negocio de prueba para desarrollo local."
        tenant.slug = "barberia-centro-turnix"
        tenant.state_id = cundinamarca.id
        tenant.city_id = girardot.id
        tenant.city = girardot.description
        tenant.plan_id = plans["premium"].id
    db.commit()

    def create_demo_user(email, password, first_name, last_name, role_name, tenant_id=None, phone=None):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            person = Person(first_name=first_name, last_name=last_name, phone=phone)
            db.add(person)
            db.flush()
            user = User(
                person_id=person.id,
                tenant_id=tenant_id,
                email=email,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = hash_password(password)
            user.tenant_id = tenant_id
        user.roles = [roles[role_name]]
        db.flush()
        return user

    business_admin = create_demo_user(
        "negocio@turnix.local",
        "Negocio123*",
        "Carlos",
        "Mendoza",
        "tenant_admin",
        tenant.id,
        "3109876543",
    )
    create_demo_user("staff@turnix.local", "Staff123*", "Laura", "Gomez", "staff", tenant.id, "3154567890")
    tenant.owner_user_id = business_admin.id
    db.commit()

    services_data = [
        {"name": "Corte de cabello", "description": "Corte clásico o moderno", "duration_minutes": 30, "price": 18000},
        {"name": "Corte y barba", "description": "Corte más arreglo de barba", "duration_minutes": 45, "price": 28000},
        {"name": "Manicura", "description": "Arreglo y esmaltado de uñas", "duration_minutes": 60, "price": 35000},
    ]
    services = []
    for item in services_data:
        service, _ = _get_or_create(db, Service, {"name": item["name"], "tenant_id": tenant.id}, item)
        for key, value in item.items():
            setattr(service, key, value)
        service.is_active = True
        services.append(service)
    db.commit()

    clients_data = [
        {"full_name": "Cliente Prueba", "username": "clienteprueba", "phone": "3159876543", "telegram_user_id": "999999999"},
        {"full_name": "Maria Garcia", "phone": "3001112222"},
    ]
    clients = []
    for item in clients_data:
        client, _ = _get_or_create(db, Client, {"full_name": item["full_name"], "tenant_id": tenant.id}, item)
        for key, value in item.items():
            setattr(client, key, value)
        clients.append(client)
    db.commit()

    today = date.today()
    for idx, client in enumerate(clients):
        service = services[idx % len(services)]
        appt_date = today + timedelta(days=idx)
        start_time = time(9 + idx, 0)
        exists = db.query(Appointment).filter(
            Appointment.tenant_id == tenant.id,
            Appointment.client_id == client.id,
            Appointment.appointment_date == appt_date,
            Appointment.start_time == start_time,
        ).first()
        if not exists:
            from datetime import datetime as dt

            end_time = (dt.combine(appt_date, start_time) + timedelta(minutes=service.duration_minutes)).time()
            db.add(
                Appointment(
                    tenant_id=tenant.id,
                    service_id=service.id,
                    client_id=client.id,
                    appointment_date=appt_date,
                    start_time=start_time,
                    end_time=end_time,
                    status="confirmed",
                    notes="Cita de prueba",
                )
            )
    db.commit()

    config = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == tenant.id).first()
    if not config:
        db.add(
            TelegramConfig(
                tenant_id=tenant.id,
                welcome_message=f"Bienvenido a {tenant.name}. ¿En qué puedo ayudarte?",
                services_message="Estos son nuestros servicios disponibles:",
                ask_date_message="¿Para qué fecha prefieres tu cita? (YYYY-MM-DD)",
                ask_time_message="Selecciona un horario disponible:",
                confirm_message="Tu cita ha sido confirmada. Te esperamos.",
                cancel_message="Tu cita ha sido cancelada.",
                allow_cancellation=True,
                show_prices=True,
                show_duration=True,
            )
        )
        db.commit()

    print("Datos de prueba creados/actualizados.")
    print("Credenciales de desarrollo:")
    print("  Negocio:  negocio@turnix.local / Negocio123*")
    print("  Staff:    staff@turnix.local   / Staff123*")
    print(f"Negocio de prueba: {tenant.name} | slug={tenant.slug} | ciudad=GIRARDOT(494)")


def run_seed():
    _warn_missing_env()
    print("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)

    db = SessionLocal()
    try:
        print("Cargando planes...")
        plans = _seed_plans(db)
        print("Cargando roles...")
        roles = _seed_roles(db)
        print("Cargando departamentos y ciudades desde archivos SQL...")
        locations = _seed_locations(db)
        print(f"Departamentos: {locations['total_states']} | Ciudades: {locations['total_cities']}")
        print("Creando/actualizando superadmin inicial...")
        superadmin = _seed_superadmin(db, roles)
        print(f"Superadmin inicial listo: {superadmin.email}")

        if settings.TURNIX_DEMO_SEED:
            print("TURNIX_DEMO_SEED=true: creando datos de prueba...")
            _create_demo_data(db, plans, roles, locations)
        else:
            print("TURNIX_DEMO_SEED=false: no se crean negocio ni usuarios demo.")

        print("Seed completado correctamente.")
        print("\nPara reiniciar datos de prueba desde cero:")
        print("  1. Cerrar el backend (o matar proceso en puerto 8000)")
        print("  2. Ejecutar: Remove-Item turnix.db -Force")
        print("  3. Ejecutar: python -m app.database.seed")
    except Exception as exc:
        db.rollback()
        print(f"ERROR en seed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
