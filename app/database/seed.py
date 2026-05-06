"""
Script de seed – Carga datos de prueba en la base de datos.

Uso:
  python -m app.database.seed
"""
import sys
import os
from datetime import date, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, create_tables
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.client import Client
from app.models.appointment import Appointment


def run_seed():
    create_tables()
    db = SessionLocal()
    try:
        # ── Negocio de prueba ──────────────────────────────
        tenant = db.query(Tenant).filter(Tenant.name == "Turnix Demo Barbería").first()
        if not tenant:
            tenant = Tenant(
                name="Turnix Demo Barbería",
                description="Barbería y salón de belleza de demostración",
                phone="300 123 4567",
                address="Calle 45 # 12-30, Bogotá",
                opening_time="08:00",
                closing_time="20:00",
                is_active=True,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Negocio creado: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"ℹ️  Negocio ya existe: {tenant.name} (ID: {tenant.id})")

        # ── Servicios de prueba ────────────────────────────
        servicios_demo = [
            {
                "name": "Corte de cabello",
                "description": "Corte clásico o moderno según tu estilo",
                "duration_minutes": 30,
                "price": 18000,
            },
            {
                "name": "Corte + Barba",
                "description": "Corte de cabello más arreglo de barba",
                "duration_minutes": 45,
                "price": 28000,
            },
            {
                "name": "Tintura",
                "description": "Coloración completa con productos profesionales",
                "duration_minutes": 90,
                "price": 70000,
            },
            {
                "name": "Manicura",
                "description": "Arreglo y esmaltado de uñas",
                "duration_minutes": 60,
                "price": 35000,
            },
        ]

        for s_data in servicios_demo:
            existing = db.query(Service).filter(
                Service.name == s_data["name"], Service.tenant_id == tenant.id
            ).first()
            if not existing:
                srv = Service(tenant_id=tenant.id, **s_data, is_active=True)
                db.add(srv)
                db.commit()
                print(f"  ✅ Servicio creado: {s_data['name']}")
            else:
                print(f"  ℹ️  Servicio ya existe: {s_data['name']}")

        # ── Cliente de prueba ──────────────────────────────
        client = db.query(Client).filter(Client.full_name == "Cliente Demo").first()
        if not client:
            client = Client(
                full_name="Cliente Demo",
                username="clientedemo",
                phone="315 987 6543",
                telegram_user_id="999999999",
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            print(f"✅ Cliente creado: {client.full_name} (ID: {client.id})")
        else:
            print(f"ℹ️  Cliente ya existe: {client.full_name} (ID: {client.id})")

        # ── Cita de prueba ─────────────────────────────────
        service = db.query(Service).filter(Service.tenant_id == tenant.id).first()
        if service:
            existing_appt = db.query(Appointment).filter(
                Appointment.client_id == client.id,
                Appointment.appointment_date == date(2026, 5, 15),
            ).first()
            if not existing_appt:
                appt = Appointment(
                    tenant_id=tenant.id,
                    service_id=service.id,
                    client_id=client.id,
                    appointment_date=date(2026, 5, 15),
                    start_time=time(10, 0),
                    end_time=time(10, 30),
                    status="confirmed",
                    notes="Cita de demostración generada por seed",
                )
                db.add(appt)
                db.commit()
                print(f"✅ Cita demo creada: {appt.appointment_date} {appt.start_time} – ID: {appt.id}")
            else:
                print("ℹ️  Cita demo ya existe.")

        print("\n🎉 Seed completado exitosamente.")
        print(f"   Negocio ID: {tenant.id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
