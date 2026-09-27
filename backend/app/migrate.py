from sqlalchemy import inspect, text

from app.database import Base, engine


def _add_column(conn, table: str, col: str, ddl: str):
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def run_migrations():
    """Lightweight SQLite migrations for schema additions."""
    with engine.begin() as conn:
        _add_column(conn, "users", "phone", "phone VARCHAR(20)")
        _add_column(conn, "users", "is_active", "is_active BOOLEAN DEFAULT 1")
        conn.execute(text("UPDATE users SET is_active = 1 WHERE is_active IS NULL"))
        _add_column(conn, "users", "reset_token", "reset_token VARCHAR(64)")
        _add_column(conn, "users", "reset_token_expires", "reset_token_expires DATETIME")

        _add_column(conn, "notifications", "status", "status VARCHAR(20) DEFAULT 'sent'")
        _add_column(conn, "notifications", "provider_ref", "provider_ref VARCHAR(100)")

        _add_column(conn, "pregnancies", "consent_recorded", "consent_recorded BOOLEAN DEFAULT 0")
        _add_column(conn, "pregnancies", "language", "language VARCHAR(5) DEFAULT 'en'")
        _add_column(conn, "pregnancies", "whatsapp_opt_in", "whatsapp_opt_in BOOLEAN DEFAULT 1")
        _add_column(conn, "pregnancies", "multiple_gestation", "multiple_gestation BOOLEAN DEFAULT 0")
        _add_column(conn, "pregnancies", "fetal_count", "fetal_count INTEGER DEFAULT 1")
        _add_column(conn, "pregnancies", "guardian_consent_recorded", "guardian_consent_recorded BOOLEAN DEFAULT 0")
        _add_column(conn, "pregnancies", "gravida", "gravida INTEGER DEFAULT 1")
        _add_column(conn, "pregnancies", "parity", "parity INTEGER DEFAULT 0")

        _add_column(conn, "danger_signs", "reporter_type", "reporter_type VARCHAR(20)")
        _add_column(conn, "danger_signs", "reporter_id", "reporter_id INTEGER")
        _add_column(conn, "danger_signs", "ai_brief", "ai_brief TEXT")

        _add_column(conn, "ai_chat_messages", "session_id", "session_id INTEGER")
        _add_column(conn, "ai_chat_messages", "message_type", "message_type VARCHAR(20) DEFAULT 'text'")
        _add_column(conn, "ai_chat_messages", "attachment_name", "attachment_name VARCHAR(255)")

    Base.metadata.create_all(bind=engine)
