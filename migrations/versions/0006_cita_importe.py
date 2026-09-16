"""Migración 0006: importe y datos de bono en la cita.

Añade a la tabla `appointments` (todas idempotentes y no destructivas):
  - amount (REAL): importe de la sesión en euros, fijado al finalizar la cita.
  - paid_with_pack (INTEGER/bool): si la sesión se pagó consumiendo un bono.
  - pack_sessions_consumed (INTEGER): nº de sesiones de bono consumidas.

Así el importe monetario (amount) queda separado de las sesiones de bono
consumidas, evitando la ambigüedad "1 € vs 1 sesión".
"""
from sqlalchemy import text


def _column_exists(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def upgrade(connection):
    if not _column_exists(connection, "appointments", "amount"):
        connection.execute(text("ALTER TABLE appointments ADD COLUMN amount REAL"))
    if not _column_exists(connection, "appointments", "paid_with_pack"):
        connection.execute(text("ALTER TABLE appointments ADD COLUMN paid_with_pack INTEGER DEFAULT 0"))
    if not _column_exists(connection, "appointments", "pack_sessions_consumed"):
        connection.execute(text("ALTER TABLE appointments ADD COLUMN pack_sessions_consumed INTEGER"))
