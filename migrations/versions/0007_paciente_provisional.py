"""Migración 0007: paciente provisional (cita sin registrar).

Añade a la tabla `patients` la columna:
  - is_provisional (INTEGER/bool): True mientras el paciente sólo tiene datos
    mínimos (nombre, teléfono, email) para una cita "sin registrar". Al completar
    su ficha clínica pasa a False.

Idempotente y no destructiva.
"""
from sqlalchemy import text


def _column_exists(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def upgrade(connection):
    if not _column_exists(connection, "patients", "is_provisional"):
        connection.execute(text("ALTER TABLE patients ADD COLUMN is_provisional BOOLEAN DEFAULT 0"))
