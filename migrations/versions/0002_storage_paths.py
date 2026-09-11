"""Migración 0002: rutas de almacenamiento configurables.

Cambios (todos NO destructivos e idempotentes):

  1. Añade la columna `pdf_filename` a la tabla `invoices` si no existe.
     Guarda el nombre relativo del PDF de cada factura (la carpeta base se
     configura en la tabla `config`).

  2. Siembra en la tabla `config` las rutas base de almacenamiento con los
     valores correctos de producción (Raspberry Pi -> USB), SOLO si la clave
     no existe todavía. De este modo no pisa una configuración ya establecida
     manualmente desde la app.

Los logs NO se incluyen: se quedan siempre en la SD y no son configurables.
"""
from sqlalchemy import text

# Rutas base por defecto en producción (Raspberry Pi). El USB se monta en /media/usb.
_DEFAULT_PATHS = {
    "storage_signed_docs_path": "/media/usb/documentos_firmados",
    "storage_invoices_path": "/media/usb/facturas",
    "storage_patient_docs_path": "/media/usb/pacientes",
    "storage_auto_backup_path": "/media/usb/backups",
}


def _column_exists(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    # PRAGMA table_info devuelve (cid, name, type, notnull, dflt_value, pk)
    return any(r[1] == column for r in rows)


def upgrade(connection):
    # 1. Columna pdf_filename en invoices (si no existe).
    if not _column_exists(connection, "invoices", "pdf_filename"):
        connection.execute(text("ALTER TABLE invoices ADD COLUMN pdf_filename TEXT"))

    # 2. Sembrar rutas base en config (solo las que falten).
    for key, value in _DEFAULT_PATHS.items():
        existing = connection.execute(
            text("SELECT 1 FROM config WHERE key = :k"), {"k": key}
        ).fetchone()
        if existing is None:
            connection.execute(
                text("INSERT INTO config (key, value) VALUES (:k, :v)"),
                {"k": key, "v": value},
            )
