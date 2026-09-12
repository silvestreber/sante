"""Migración 0004: eliminar tablas residuales sin uso.

- `signed_consents`: quedó en desuso tras unificar todo en `patient_documents`
  (migración 0003). Su modelo ya se eliminó del código.
- `clinic_settings`: tabla huérfana de una versión antigua; ningún modelo la usa
  (la configuración vive en la tabla `config`).

Idempotente: usa DROP TABLE IF EXISTS.
"""
from sqlalchemy import text


def upgrade(connection):
    connection.execute(text("DROP TABLE IF EXISTS signed_consents"))
    connection.execute(text("DROP TABLE IF EXISTS clinic_settings"))
