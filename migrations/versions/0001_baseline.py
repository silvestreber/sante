"""Migración baseline (0001).

No modifica el esquema: sirve como punto de partida del sistema de migraciones
y para verificar que el runner funciona en producción. Las tablas ya se crean
con Base.metadata.create_all() al arrancar la app; esta migración solo deja
constancia de la línea base.

Las próximas migraciones (0002, 0003, ...) contendrán los ALTER TABLE / cambios
de esquema reales, siempre de forma no destructiva.
"""
from sqlalchemy import text


def upgrade(connection):
    # Baseline: sin cambios de esquema. Comprobación inocua de conectividad.
    connection.execute(text("SELECT 1"))
