"""
Script de seed – Carga datos de demostración en la base de datos.

Elimina y recrea el esquema para garantizar coherencia.

Uso:
  python -m app.database.seed
"""
import sys
import os
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
import app.models  # noqa – importa todos los modelos
from app.core.database import Base


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _get_or_create(db, Model, filter_kwargs, create_kwargs=None):
    obj = db.query(Model).filter_by(**filter_kwargs).first()
    if not obj:
        kwargs = {**filter_kwargs, **(create_kwargs or {})}
        obj = Model(**kwargs)
        db.add(obj)
        db.flush()
        return obj, True
    return obj, False


# ──────────────────────────────────────────────────────────
def run_seed():
    print("🗑️  Eliminando esquema anterior…")
    Base.metadata.drop_all(bind=engine)
    print("🏗️  Creando esquema nuevo…")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.models.plan import Plan
        from app.models.location import State, City
        from app.models.person import Person
        from app.models.user import User, Role, Permission
        from app.models.tenant import Tenant
        from app.models.service import Service
        from app.models.client import Client
        from app.models.appointment import Appointment
        from app.models.telegram_config import TelegramConfig

        # ── Planes ────────────────────────────────────────
        print("\n📦 Creando planes…")
        plan_free, _ = _get_or_create(db, Plan,
            {"name": "free"},
            {"display_name": "Gratuito", "max_appointments_monthly": 30,
             "max_active_services": 5, "max_staff": 1,
             "allows_advanced_reminders": False, "allows_analytics": False})

        plan_premium, _ = _get_or_create(db, Plan,
            {"name": "premium"},
            {"display_name": "Premium", "max_appointments_monthly": 200,
             "max_active_services": 20, "max_staff": 5,
             "allows_advanced_reminders": True, "allows_analytics": True})

        plan_enterprise, _ = _get_or_create(db, Plan,
            {"name": "enterprise"},
            {"display_name": "Empresarial", "max_appointments_monthly": None,
             "max_active_services": None, "max_staff": None,
             "allows_advanced_reminders": True, "allows_analytics": True})

        db.commit()
        print("  ✅ Planes: Gratuito, Premium, Empresarial")

        # ── Roles ─────────────────────────────────────────
        print("\n🎭 Creando roles…")
        roles_data = [
            ("superadmin", "Superadministrador de la plataforma Turnix"),
            ("tenant_admin", "Administrador de un negocio"),
            ("staff", "Personal / trabajador del negocio"),
            ("customer", "Cliente final"),
        ]
        role_map = {}
        for rname, rdesc in roles_data:
            role, created = _get_or_create(db, Role, {"name": rname}, {"description": rdesc})
            role_map[rname] = role
            if created:
                print(f"  ✅ Rol creado: {rname}")
        db.commit()

        # ── Departamentos y ciudades de Colombia ───────────
        print("\n🗺️  Creando departamentos y ciudades…")
        departamentos = {
            "Bogotá D.C.":    ["Bogotá"],
            "Cundinamarca":   ["Girardot", "Soacha", "Fusagasugá", "Facatativá",
                               "Zipaquirá", "Chía", "Mosquera", "Madrid", "Funza"],
            "Antioquia":      ["Medellín", "Bello", "Itagüí", "Envigado", "Rionegro", "Sabaneta"],
            "Valle del Cauca":["Cali", "Buenaventura", "Palmira", "Tuluá", "Buga"],
            "Atlántico":      ["Barranquilla", "Soledad", "Malambo", "Sabanalarga"],
            "Santander":      ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta"],
            "Bolívar":        ["Cartagena", "Magangué", "El Carmen de Bolívar"],
            "Nariño":         ["Pasto", "Tumaco", "Ipiales"],
            "Boyacá":         ["Tunja", "Duitama", "Sogamoso"],
            "Córdoba":        ["Montería", "Cereté", "Sahagún"],
            "Meta":           ["Villavicencio", "Acacías", "Granada"],
            "Tolima":         ["Ibagué", "Espinal", "Honda"],
        }
        state_map_geo = {}
        for dep_name, ciudades in departamentos.items():
            dep, _ = _get_or_create(db, State, {"name": dep_name})
            db.flush()
            state_map_geo[dep_name] = dep
            for ciudad_name in ciudades:
                _get_or_create(db, City, {"name": ciudad_name, "state_id": dep.id})
            db.flush()
        db.commit()
        print(f"  ✅ {len(departamentos)} departamentos con ciudades creados (incluye Cundinamarca/Girardot)")

        # Referencia de ciudad para usuarios demo
        city = db.query(City).filter(City.name == "Bogotá").first()

        # ── Tenant demo ────────────────────────────────────
        print("\n🏢 Creando tenant de demostración…")
        demo_tenant = db.query(Tenant).filter(Tenant.slug == "barberia-demo").first()
        if not demo_tenant:
            demo_tenant = Tenant(
                name="Barbería Demo Turnix",
                description="Negocio de demostración para la plataforma Turnix",
                phone="+57 300 123 4567",
                address="Calle 45 # 12-30, Bogotá",
                city="Bogotá",
                slug="barberia-demo",
                opening_time="08:00",
                closing_time="20:00",
                plan_id=plan_premium.id,
                is_active=True,
            )
            db.add(demo_tenant)
            db.flush()
            print(f"  ✅ Tenant creado: {demo_tenant.name} (slug: barberia-demo)")
        else:
            print(f"  ℹ️  Tenant ya existe: {demo_tenant.name}")
        db.commit()

        # ── Usuarios demo ──────────────────────────────────
        print("\n👤 Creando usuarios demo…")

        def _create_user(email, password, first_name, last_name, role_name, tenant_id=None, phone=None):
            person, _ = _get_or_create(db, Person,
                {"first_name": first_name, "last_name": last_name},
                {"phone": phone, "city_id": city.id})
            db.flush()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    person_id=person.id,
                    tenant_id=tenant_id,
                    email=email,
                    password_hash=hash_password(password),
                    is_active=True,
                )
                db.add(user)
                db.flush()
                print(f"  ✅ Usuario: {email} [{role_name}]")
            else:
                user.password_hash = hash_password(password)
                user.tenant_id = tenant_id
            user.roles = [role_map[role_name]]
            db.flush()
            return user

        superadmin = _create_user(
            "admin@turnix.demo", "Admin123*",
            "Admin", "Turnix", "superadmin"
        )
        negocio_admin = _create_user(
            "negocio@turnix.demo", "Negocio123*",
            "Carlos", "Mendoza", "tenant_admin", tenant_id=demo_tenant.id, phone="+57 310 987 6543"
        )
        staff_user = _create_user(
            "staff@turnix.demo", "Staff123*",
            "Laura", "Gómez", "staff", tenant_id=demo_tenant.id, phone="+57 315 456 7890"
        )
        db.commit()

        # Vincular dueño al tenant
        demo_tenant.owner_user_id = negocio_admin.id
        db.commit()
        print(f"  ✅ Propietario del tenant: {negocio_admin.email}")

        # ── Servicios demo ─────────────────────────────────
        print("\n✂️  Creando servicios…")
        servicios_demo = [
            {"name": "Corte de cabello", "description": "Corte clásico o moderno", "duration_minutes": 30, "price": 18000},
            {"name": "Corte + Barba", "description": "Corte de cabello más arreglo de barba", "duration_minutes": 45, "price": 28000},
            {"name": "Tintura", "description": "Coloración completa con productos profesionales", "duration_minutes": 90, "price": 70000},
            {"name": "Manicura", "description": "Arreglo y esmaltado de uñas", "duration_minutes": 60, "price": 35000},
            {"name": "Pedicura", "description": "Tratamiento y esmaltado de pies", "duration_minutes": 60, "price": 40000},
        ]
        services_created = []
        for s_data in servicios_demo:
            svc, created = _get_or_create(db, Service,
                {"name": s_data["name"], "tenant_id": demo_tenant.id},
                {**s_data, "is_active": True})
            services_created.append(svc)
            if created:
                print(f"  ✅ Servicio: {s_data['name']}")
        db.commit()

        # ── Clientes demo ──────────────────────────────────
        print("\n👥 Creando clientes demo…")
        clientes_demo = [
            {"full_name": "Cliente Demo", "username": "clientedemo", "phone": "315 987 6543", "telegram_user_id": "999999999"},
            {"full_name": "María García", "phone": "300 111 2222"},
            {"full_name": "Juan Pérez", "phone": "311 333 4444"},
            {"full_name": "Ana Torres", "phone": "312 555 6666"},
            {"full_name": "Pedro Rojas", "phone": "313 777 8888"},
        ]
        clients_created = []
        for c_data in clientes_demo:
            client, created = _get_or_create(db, Client,
                {"full_name": c_data["full_name"], "tenant_id": demo_tenant.id},
                {**c_data})
            clients_created.append(client)
            if created:
                print(f"  ✅ Cliente: {c_data['full_name']}")
        db.commit()

        # ── Citas demo ─────────────────────────────────────
        print("\n📅 Creando citas demo…")
        today = date.today()
        citas_demo = [
            # Pasadas (para métricas del mes)
            {"days": -5, "hour": 9,  "svc_idx": 0, "cli_idx": 0, "status": "completed"},
            {"days": -4, "hour": 10, "svc_idx": 1, "cli_idx": 1, "status": "completed"},
            {"days": -3, "hour": 11, "svc_idx": 2, "cli_idx": 2, "status": "cancelled"},
            {"days": -2, "hour": 14, "svc_idx": 3, "cli_idx": 3, "status": "completed"},
            {"days": -1, "hour": 15, "svc_idx": 0, "cli_idx": 4, "status": "completed"},
            # Hoy
            {"days":  0, "hour": 9,  "svc_idx": 0, "cli_idx": 1, "status": "confirmed"},
            {"days":  0, "hour": 10, "svc_idx": 1, "cli_idx": 2, "status": "pending"},
            {"days":  0, "hour": 14, "svc_idx": 3, "cli_idx": 3, "status": "confirmed"},
            # Futuras
            {"days":  1, "hour": 10, "svc_idx": 0, "cli_idx": 0, "status": "confirmed"},
            {"days":  2, "hour": 11, "svc_idx": 2, "cli_idx": 4, "status": "pending"},
            {"days":  3, "hour": 9,  "svc_idx": 1, "cli_idx": 1, "status": "confirmed"},
        ]
        for i, cita in enumerate(citas_demo):
            appt_date = today + timedelta(days=cita["days"])
            svc = services_created[cita["svc_idx"]]
            cli = clients_created[cita["cli_idx"]]
            start_t = time(cita["hour"], 0)
            from datetime import datetime, timedelta as td
            end_dt = datetime.combine(appt_date, start_t) + td(minutes=svc.duration_minutes)
            end_t = end_dt.time()
            # Verificar si ya existe
            existing = db.query(Appointment).filter(
                Appointment.tenant_id == demo_tenant.id,
                Appointment.appointment_date == appt_date,
                Appointment.start_time == start_t,
                Appointment.client_id == cli.id,
            ).first()
            if not existing:
                appt = Appointment(
                    tenant_id=demo_tenant.id,
                    service_id=svc.id,
                    client_id=cli.id,
                    appointment_date=appt_date,
                    start_time=start_t,
                    end_time=end_t,
                    status=cita["status"],
                    notes="Cita de demostración",
                )
                db.add(appt)
        db.commit()
        total_appts = db.query(Appointment).filter(Appointment.tenant_id == demo_tenant.id).count()
        print(f"  ✅ Citas creadas: {total_appts} en total")

        # ── Configuración Telegram demo ────────────────────
        print("\n🤖 Configurando Telegram para negocio demo…")
        tg_cfg = db.query(TelegramConfig).filter(TelegramConfig.tenant_id == demo_tenant.id).first()
        if not tg_cfg:
            tg_cfg = TelegramConfig(
                tenant_id=demo_tenant.id,
                welcome_message=f"¡Hola! Bienvenido/a a *{demo_tenant.name}*. ¿En qué puedo ayudarte?",
                services_message="Estos son nuestros servicios disponibles:",
                ask_date_message="¿Qué fecha prefieres? (Formato: DD/MM/AAAA)",
                ask_time_message="¿A qué hora te gustaría tu cita?",
                confirm_message="✅ ¡Tu cita ha sido confirmada! Te esperamos.",
                cancel_message="Tu cita ha sido cancelada. ¡Hasta pronto!",
                allow_cancellation=True,
                show_prices=True,
                show_duration=True,
                use_global_bot=True,
            )
            db.add(tg_cfg)
            db.commit()
            print(f"  ✅ Configuración de Telegram creada para: {demo_tenant.name}")
        else:
            print(f"  ℹ️  Configuración Telegram ya existe para: {demo_tenant.name}")

        print("\n" + "="*52)
        print("🎉 Seed completado exitosamente")
        print("="*52)
        print("\n📋 CREDENCIALES DE ACCESO DEMO:")
        print("  Superadmin:   admin@turnix.demo    / Admin123*")
        print("  Negocio:      negocio@turnix.demo  / Negocio123*")
        print("  Personal:     staff@turnix.demo    / Staff123*")
        print(f"\n🏢 Tenant demo: '{demo_tenant.name}' (ID: {demo_tenant.id})")
        print("⚠️  Estos datos son SOLO para demostración.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error en seed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
