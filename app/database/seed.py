# -*- coding: utf-8 -*-
"""
Script de seed - Carga datos de demostracion en la base de datos.

Elimina y recrea el esquema para garantizar coherencia.
Carga departamentos y ciudades desde:
  app/database/raw/state.sql
  app/database/raw/city.sql

Uso:
  python -m app.database.seed
"""
import re
import sys
import os
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
import app.models  # noqa
from app.core.database import Base

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAW_DIR = os.path.join(_HERE, "raw")


def _get_or_create(db, Model, filter_kwargs, create_kwargs=None):
    obj = db.query(Model).filter_by(**filter_kwargs).first()
    if not obj:
        kwargs = {**filter_kwargs, **(create_kwargs or {})}
        obj = Model(**kwargs)
        db.add(obj)
        db.flush()
        return obj, True
    return obj, False


def _parse_state_sql(path):
    text = open(path, encoding="utf-8").read()
    rows = re.findall(r"\((\d+),\s*'([^']+)',\s*'([^']+)'\)", text)
    return [{"id": int(i), "code": c, "description": d} for i, c, d in rows]


def _parse_city_sql(path):
    text = open(path, encoding="utf-8").read()
    rows = re.findall(r"\((\d+),\s*'([^']+)',\s*'([^']+)',\s*(\d+)\)", text)
    return [{"id": int(i), "code": c, "description": d, "state_id": int(s)} for i, c, d, s in rows]


def run_seed():
    print("Eliminando esquema anterior...")
    Base.metadata.drop_all(bind=engine)
    print("Creando esquema nuevo...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.models.plan import Plan
        from app.models.location import State, City
        from app.models.person import Person
        from app.models.user import User, Role
        from app.models.tenant import Tenant
        from app.models.service import Service
        from app.models.client import Client
        from app.models.appointment import Appointment
        from app.models.telegram_config import TelegramConfig

        print("\n[1/8] Creando planes...")
        plan_free, _ = _get_or_create(db, Plan, {"name": "free"},
            {"display_name": "Gratuito", "max_appointments_monthly": 30,
             "max_active_services": 5, "max_staff": 1,
             "allows_advanced_reminders": False, "allows_analytics": False})
        plan_premium, _ = _get_or_create(db, Plan, {"name": "premium"},
            {"display_name": "Premium", "max_appointments_monthly": 200,
             "max_active_services": 20, "max_staff": 5,
             "allows_advanced_reminders": True, "allows_analytics": True})
        plan_enterprise, _ = _get_or_create(db, Plan, {"name": "enterprise"},
            {"display_name": "Empresarial", "max_appointments_monthly": None,
             "max_active_services": None, "max_staff": None,
             "allows_advanced_reminders": True, "allows_analytics": True})
        db.commit()
        print("  OK Planes creados")

        print("\n[2/8] Creando roles...")
        roles_data = [
            ("superadmin", "Superadministrador de la plataforma Turnix"),
            ("tenant_admin", "Administrador de un negocio"),
            ("staff", "Personal del negocio"),
            ("customer", "Cliente final"),
        ]
        role_map = {}
        for rname, rdesc in roles_data:
            role, _ = _get_or_create(db, Role, {"name": rname}, {"description": rdesc})
            role_map[rname] = role
        db.commit()
        print("  OK Roles creados")

        print("\n[3/8] Cargando departamentos desde state.sql...")
        states_data = _parse_state_sql(os.path.join(_RAW_DIR, "state.sql"))
        for s in states_data:
            ex = db.query(State).filter(State.id == s["id"]).first()
            if not ex:
                db.add(State(id=s["id"], code=s["code"], description=s["description"]))
            else:
                ex.code = s["code"]; ex.description = s["description"]
        db.flush(); db.commit()
        total_states = db.query(State).count()
        print(f"  OK {total_states} departamentos cargados")
        cundinamarca = db.query(State).filter(State.id == 11).first()
        assert cundinamarca and cundinamarca.description == "CUNDINAMARCA"
        print(f"  OK CUNDINAMARCA id=11 code={cundinamarca.code}")

        print("\n[4/8] Cargando ciudades desde city.sql...")
        cities_data = _parse_city_sql(os.path.join(_RAW_DIR, "city.sql"))
        for c in cities_data:
            ex = db.query(City).filter(City.id == c["id"]).first()
            if not ex:
                db.add(City(id=c["id"], code=c["code"], description=c["description"], state_id=c["state_id"]))
            else:
                ex.code = c["code"]; ex.description = c["description"]; ex.state_id = c["state_id"]
        db.flush(); db.commit()
        total_cities = db.query(City).count()
        print(f"  OK {total_cities} ciudades cargadas")
        girardot = db.query(City).filter(City.id == 494).first()
        assert girardot and girardot.state_id == 11
        print(f"  OK GIRARDOT id=494 code={girardot.code} state_id={girardot.state_id}")

        bogota_city = db.query(City).filter(City.description == "BOGOTA").first()
        if not bogota_city:
            bogota_city = db.query(City).filter(City.state_id == 3).first()
        ref_city_id = bogota_city.id if bogota_city else girardot.id

        print("\n[5/8] Creando tenant de demostracion...")
        demo_tenant = db.query(Tenant).filter(Tenant.slug == "barberia-demo").first()
        if not demo_tenant:
            demo_tenant = Tenant(
                name="Barberia Demo Turnix",
                description="Negocio de demostracion para la plataforma Turnix",
                phone="3001234567",
                address="Carrera 10 # 15-20, Girardot",
                city=girardot.description,
                state_id=cundinamarca.id,
                city_id=girardot.id,
                slug="barberia-demo",
                opening_time="08:00",
                closing_time="20:00",
                plan_id=plan_premium.id,
                is_active=True,
            )
            db.add(demo_tenant); db.flush()
            print(f"  OK Tenant creado: {demo_tenant.name}")
        else:
            demo_tenant.state_id = cundinamarca.id
            demo_tenant.city_id = girardot.id
            demo_tenant.city = girardot.description
            db.flush()
            print(f"  OK Tenant actualizado: {demo_tenant.name}")
        db.commit()

        print("\n[6/8] Creando usuarios demo...")

        def _create_user(email, password, first_name, last_name, role_name, tenant_id=None, phone=None):
            person, _ = _get_or_create(db, Person,
                {"first_name": first_name, "last_name": last_name},
                {"phone": phone, "city_id": ref_city_id})
            db.flush()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(person_id=person.id, tenant_id=tenant_id, email=email,
                            password_hash=hash_password(password), is_active=True)
                db.add(user); db.flush()
                print(f"  OK Usuario: {email} [{role_name}]")
            else:
                user.password_hash = hash_password(password)
                user.tenant_id = tenant_id
            user.roles = [role_map[role_name]]
            db.flush()
            return user

        superadmin = _create_user("admin@turnix.demo", "Admin123*", "Admin", "Turnix", "superadmin")
        negocio_admin = _create_user("negocio@turnix.demo", "Negocio123*", "Carlos", "Mendoza",
                                     "tenant_admin", tenant_id=demo_tenant.id, phone="3109876543")
        staff_user = _create_user("staff@turnix.demo", "Staff123*", "Laura", "Gomez",
                                  "staff", tenant_id=demo_tenant.id, phone="3154567890")
        db.commit()
        demo_tenant.owner_user_id = negocio_admin.id
        db.commit()
        print(f"  OK Propietario: {negocio_admin.email}")

        print("\n[7/8] Creando servicios, clientes y citas demo...")
        servicios_demo = [
            {"name": "Corte de cabello", "description": "Corte clasico o moderno", "duration_minutes": 30, "price": 18000},
            {"name": "Corte + Barba", "description": "Corte mas arreglo de barba", "duration_minutes": 45, "price": 28000},
            {"name": "Tintura", "description": "Coloracion completa", "duration_minutes": 90, "price": 70000},
            {"name": "Manicura", "description": "Arreglo y esmaltado de unas", "duration_minutes": 60, "price": 35000},
            {"name": "Pedicura", "description": "Tratamiento y esmaltado de pies", "duration_minutes": 60, "price": 40000},
        ]
        services_created = []
        for s_data in servicios_demo:
            svc, _ = _get_or_create(db, Service, {"name": s_data["name"], "tenant_id": demo_tenant.id},
                                    {**s_data, "is_active": True})
            services_created.append(svc)
        db.commit()
        print(f"  OK {len(services_created)} servicios")

        clientes_demo = [
            {"full_name": "Cliente Demo", "username": "clientedemo", "phone": "315 987 6543", "telegram_user_id": "999999999"},
            {"full_name": "Maria Garcia", "phone": "300 111 2222"},
            {"full_name": "Juan Perez",   "phone": "311 333 4444"},
            {"full_name": "Ana Torres",   "phone": "312 555 6666"},
            {"full_name": "Pedro Rojas",  "phone": "313 777 8888"},
        ]
        clients_created = []
        for c_data in clientes_demo:
            client, _ = _get_or_create(db, Client,
                {"full_name": c_data["full_name"], "tenant_id": demo_tenant.id}, {**c_data})
            clients_created.append(client)
        db.commit()
        print(f"  OK {len(clients_created)} clientes")

        today = date.today()
        citas_demo = [
            {"days": -5, "hour": 9,  "svc_idx": 0, "cli_idx": 0, "status": "completed"},
            {"days": -4, "hour": 10, "svc_idx": 1, "cli_idx": 1, "status": "completed"},
            {"days": -3, "hour": 11, "svc_idx": 2, "cli_idx": 2, "status": "cancelled"},
            {"days": -2, "hour": 14, "svc_idx": 3, "cli_idx": 3, "status": "completed"},
            {"days": -1, "hour": 15, "svc_idx": 0, "cli_idx": 4, "status": "completed"},
            {"days":  0, "hour":  9, "svc_idx": 0, "cli_idx": 1, "status": "confirmed"},
            {"days":  0, "hour": 10, "svc_idx": 1, "cli_idx": 2, "status": "pending"},
            {"days":  0, "hour": 14, "svc_idx": 3, "cli_idx": 3, "status": "confirmed"},
            {"days":  1, "hour": 10, "svc_idx": 0, "cli_idx": 0, "status": "confirmed"},
            {"days":  2, "hour": 11, "svc_idx": 2, "cli_idx": 4, "status": "pending"},
            {"days":  3, "hour":  9, "svc_idx": 1, "cli_idx": 1, "status": "confirmed"},
        ]
        from datetime import datetime as _dt, timedelta as td
        for cita in citas_demo:
            appt_date = today + timedelta(days=cita["days"])
            svc = services_created[cita["svc_idx"]]
            cli = clients_created[cita["cli_idx"]]
            start_t = time(cita["hour"], 0)
            end_t = (_dt.combine(appt_date, start_t) + td(minutes=svc.duration_minutes)).time()
            ex = db.query(Appointment).filter(
                Appointment.tenant_id == demo_tenant.id,
                Appointment.appointment_date == appt_date,
                Appointment.start_time == start_t,
                Appointment.client_id == cli.id,
            ).first()
            if not ex:
                db.add(Appointment(tenant_id=demo_tenant.id, service_id=svc.id, client_id=cli.id,
                                   appointment_date=appt_date, start_time=start_t, end_time=end_t,
                                   status=cita["status"], notes="Cita de demostracion"))
        db.commit()
        total_appts = db.query(Appointment).filter(Appointment.tenant_id == demo_tenant.id).count()
        print(f"  OK {total_appts} citas")

        print("\n[8/8] Configurando Telegram para negocio demo...")
        tg_cfg = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == demo_tenant.id).first()
        if not tg_cfg:
            db.add(TelegramConfig(
                tenant_id=demo_tenant.id,
                welcome_message=f"Hola! Bienvenido/a a {demo_tenant.name}.",
                services_message="Estos son nuestros servicios disponibles:",
                ask_date_message="Que fecha prefieres? (Formato: DD/MM/AAAA)",
                ask_time_message="A que hora te gustaria tu cita?",
                confirm_message="Tu cita ha sido confirmada! Te esperamos.",
                cancel_message="Tu cita ha sido cancelada. Hasta pronto!",
                allow_cancellation=True, show_prices=True, show_duration=True, use_global_bot=True,
            ))
            db.commit()
            print("  OK Telegram configurado")

        print("\n" + "=" * 56)
        print("Seed completado exitosamente")
        print("=" * 56)
        print("\nCREDENCIALES DE ACCESO DEMO:")
        print("  Superadmin:   admin@turnix.demo    / Admin123*")
        print("  Negocio:      negocio@turnix.demo  / Negocio123*")
        print("  Personal:     staff@turnix.demo    / Staff123*")
        print(f"\nTenant demo ID={demo_tenant.id} | Depto=CUNDINAMARCA(11) | Ciudad=GIRARDOT(494)")
        print(f"Total departamentos: {total_states} | Total ciudades: {total_cities}")

    except Exception as e:
        db.rollback()
        print(f"\nERROR en seed: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()