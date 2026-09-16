"""Migración 0005: firma del fisioterapeuta.

Añade la columna `signature` a la tabla `users` si no existe. Guarda la firma
manuscrita del fisio (dataURL PNG en base64), que se estampa en los justificantes
de asistencia.

Cambio NO destructivo e idempotente.
"""
from sqlalchemy import text


def _column_exists(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    # PRAGMA table_info devuelve (cid, name, type, notnull, dflt_value, pk)
    return any(r[1] == column for r in rows)


def upgrade(connection):
    if not _column_exists(connection, "users", "signature"):
        connection.execute(text("ALTER TABLE users ADD COLUMN signature TEXT"))
