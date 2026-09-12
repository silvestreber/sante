"""Migración 0003: unificar consentimientos firmados en patient_documents.

A partir de ahora los consentimientos firmados y sus revocaciones se guardan como
documentos normales del paciente (tabla `patient_documents`), no en una tabla
aparte. Esta migración traspasa cualquier registro existente de `signed_consents`
a `patient_documents` (en producción hay 0, así que normalmente no hace nada) y es
idempotente.

No borra la tabla `signed_consents` (SQLite no soporta DROP COLUMN/TABLE de forma
sencilla y conservarla vacía es inocuo); simplemente deja de usarse.
"""
from sqlalchemy import text


def _table_exists(connection, table: str) -> bool:
    row = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table},
    ).fetchone()
    return row is not None


def upgrade(connection):
    # Si no existe la tabla antigua, nada que hacer.
    if not _table_exists(connection, "signed_consents"):
        return

    # Traspasar consentimientos vigentes (pdf_path) y revocaciones (revocation_pdf_path)
    # a patient_documents, evitando duplicar si la migración se re-ejecuta.
    rows = connection.execute(text(
        "SELECT id, patient_id, template_name, pdf_path, revocation_pdf_path, "
        "signed_at, revoked_at FROM signed_consents"
    )).fetchall()

    for r in rows:
        sc_id, patient_id, template_name, pdf_path, revocation_pdf_path, signed_at, revoked_at = r
        label = (template_name or "Consentimiento").replace(".docx", "")

        # Documento del consentimiento firmado.
        if pdf_path:
            filename = f"{label}.pdf"
            exists = connection.execute(
                text("SELECT 1 FROM patient_documents WHERE patient_id=:p AND filepath=:f"),
                {"p": patient_id, "f": pdf_path},
            ).fetchone()
            if not exists:
                connection.execute(
                    text("INSERT INTO patient_documents (patient_id, filename, filepath, description, uploaded_at) "
                         "VALUES (:p, :fn, :fp, NULL, :ts)"),
                    {"p": patient_id, "fn": filename, "fp": pdf_path, "ts": signed_at},
                )

        # Documento de la revocación (si lo hubiera).
        if revocation_pdf_path:
            filename = f"Revocación - {label}.pdf"
            exists = connection.execute(
                text("SELECT 1 FROM patient_documents WHERE patient_id=:p AND filepath=:f"),
                {"p": patient_id, "f": revocation_pdf_path},
            ).fetchone()
            if not exists:
                connection.execute(
                    text("INSERT INTO patient_documents (patient_id, filename, filepath, description, uploaded_at) "
                         "VALUES (:p, :fn, :fp, NULL, :ts)"),
                    {"p": patient_id, "fn": filename, "fp": revocation_pdf_path, "ts": revoked_at or signed_at},
                )
