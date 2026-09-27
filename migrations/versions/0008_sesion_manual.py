"""Migración 0008: sesiones clínicas manuales.

Prepara la tabla `clinical_sessions` para registrar sesiones anteriores o
externas a la clínica (sin cita asociada):
  - Añade la columna is_manual (INTEGER/bool): True si la sesión se registró a
    mano en el historial (no proviene de una cita).
  - Relaja las restricciones NOT NULL de appointment_id y physio_id (una sesión
    manual no tiene cita ni, necesariamente, fisioterapeuta asignado).

SQLite no permite quitar NOT NULL con ALTER TABLE, así que si detectamos que
appointment_id o physio_id siguen siendo NOT NULL reconstruimos la tabla
conservando todos los datos. Idempotente y no destructiva.
"""
from sqlalchemy import text


def _column_exists(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def _column_not_null(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    for r in rows:
        # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
        if r[1] == column:
            return bool(r[3])
    return False


def upgrade(connection):
    if not connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='clinical_sessions'")
    ).fetchone():
        return  # la tabla aún no existe

    # 1) Columna is_manual
    if not _column_exists(connection, "clinical_sessions", "is_manual"):
        connection.execute(text("ALTER TABLE clinical_sessions ADD COLUMN is_manual BOOLEAN DEFAULT 0"))

    # 2) Relajar NOT NULL de appointment_id y physio_id (reconstruir la tabla).
    needs_rebuild = (
        _column_not_null(connection, "clinical_sessions", "appointment_id")
        or _column_not_null(connection, "clinical_sessions", "physio_id")
    )
    if needs_rebuild:
        connection.execute(text("ALTER TABLE clinical_sessions RENAME TO clinical_sessions_old"))
        connection.execute(text(
            """
            CREATE TABLE clinical_sessions (
                id INTEGER NOT NULL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                appointment_id INTEGER REFERENCES appointments(id),
                physio_id INTEGER REFERENCES users(id),
                date DATETIME,
                observations TEXT,
                is_manual BOOLEAN DEFAULT 0
            )
            """
        ))
        connection.execute(text(
            """
            INSERT INTO clinical_sessions
                (id, patient_id, appointment_id, physio_id, date, observations, is_manual)
            SELECT id, patient_id, appointment_id, physio_id, date, observations,
                   COALESCE(is_manual, 0)
            FROM clinical_sessions_old
            """
        ))
        connection.execute(text("DROP TABLE clinical_sessions_old"))
        connection.execute(text("CREATE INDEX ix_clinical_sessions_id ON clinical_sessions (id)"))
