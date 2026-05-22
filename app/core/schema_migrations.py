"""Migraciones ligeras para desarrollo local con SQLite/create_all."""
from sqlalchemy import inspect, text


def _add_columns_if_missing(engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, ddl in missing:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


def ensure_schema_compatibility(engine) -> None:
    """Agrega columnas nuevas cuando una base SQLite ya existia antes del cambio."""
    _add_columns_if_missing(
        engine,
        "telegram_configs",
        {
            "bot_token_encrypted": "TEXT",
            "bot_id": "VARCHAR",
            "bot_commands": "TEXT",
            "internal_logo_path": "VARCHAR",
            "internal_logo_updated_at": "DATETIME",
            "is_connected": "BOOLEAN DEFAULT 0",
            "connection_status": "VARCHAR DEFAULT 'not_connected'",
            "listener_status": "VARCHAR DEFAULT 'inactive'",
            "listener_started_at": "DATETIME",
            "last_message_received_at": "DATETIME",
            "last_bot_error": "TEXT",
            "ask_name_message": "TEXT",
            "ask_phone_message": "TEXT",
            "ask_service_message": "TEXT",
            "goodbye_message": "TEXT",
            "plan_limit_public_message": "TEXT",
            "reminder_30_message": "TEXT",
            "reminder_15_message": "TEXT",
            "collect_phone": "BOOLEAN DEFAULT 1",
            "require_confirmation": "BOOLEAN DEFAULT 1",
            "auto_start_on_greeting": "BOOLEAN DEFAULT 0",
        },
    )
    _add_columns_if_missing(
        engine,
        "tenants",
        {
            "status": "VARCHAR DEFAULT 'active'",
            "archived_at": "DATETIME",
            "deleted_at": "DATETIME",
            "weekly_schedule": "JSON",
            "base_slot_minutes": "INTEGER DEFAULT 30",
            "min_booking_notice_minutes": "INTEGER DEFAULT 30",
            "max_booking_days": "INTEGER DEFAULT 30",
            "blocked_dates": "JSON",
            "blocked_time_ranges": "JSON",
            "is_test_environment": "BOOLEAN DEFAULT 0",
        },
    )
    _add_columns_if_missing(
        engine,
        "appointments",
        {
            "reminder_30_sent_at": "DATETIME",
            "reminder_15_sent_at": "DATETIME",
        },
    )
    _add_columns_if_missing(
        engine,
        "conversations",
        {
            "bot_id": "VARCHAR",
            "current_step": "VARCHAR",
            "context_data": "TEXT",
        },
    )
    _add_columns_if_missing(
        engine,
        "channels",
        {
            "bot_token_encrypted": "TEXT",
            "bot_token_masked": "VARCHAR",
        },
    )

