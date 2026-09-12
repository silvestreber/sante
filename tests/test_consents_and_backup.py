"""Tests del flujo de documentos/consentimientos (diseño unificado) y auto-backup.

Tras el rediseño, los consentimientos ya no son una entidad con estado propio:
firmar o revocar genera un PatientDocument más. Los tests que requieren generar
el PDF real (LibreOffice/Word) se saltan si la conversión no está disponible en
el entorno de test.
"""
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from tests.conftest import create_admin, create_patient, login
from app.db.models import PatientDocument


def _conversion_available() -> bool:
    """True si se puede convertir docx->pdf en este entorno (LibreOffice o Word)."""
    import sys
    if sys.platform.startswith("win"):
        try:
            import docx2pdf  # noqa
            # docx2pdf requiere Word instalado y arrancable; asumimos que en CI no está.
            return False
        except Exception:
            return False
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


# --- Plantillas de consentimiento ---

def test_consent_templates_lists_all(client, db):
    """consent-templates devuelve todas las plantillas .docx disponibles."""
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    # Ya no se filtran por firmadas: todas aparecen siempre.
    assert all("filename" in t and "name" in t for t in data)


def test_templates_exclude_temp_files(client, db):
    """La lista de plantillas no incluye ficheros temporales de Word (~$)."""
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    for t in res.json():
        assert not t["filename"].startswith("~$")


def test_view_template_pdf_endpoint(client, db):
    """El endpoint sirve el PDF en blanco de una plantilla."""
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    res = client.get(f"/api/documents/consent-template-pdf/{template}", headers=headers)
    # Puede ser 200 (si el blank pdf existe) o 404 (si no se pudo generar en este entorno).
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        assert res.headers["content-type"] == "application/pdf"


# --- Firma genera un documento del paciente ---

@pytest.mark.skipif(not _conversion_available(), reason="Conversión docx->pdf no disponible en este entorno")
def test_sign_consent_creates_patient_document(client, db):
    """Firmar un consentimiento crea un PatientDocument (lista unificada)."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    sign_res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Fisio", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert sign_res.status_code == 200
    assert "filename" in sign_res.json()

    # Aparece en la lista de documentos del paciente.
    res = client.get(f"/api/patients/{patient.id}/documents", headers=headers)
    docs = res.json()
    assert len(docs) == 1
    assert docs[0]["is_pdf"] is True


def test_sign_consent_nonexistent_patient(client, db):
    """Firmar para un paciente inexistente devuelve 404."""
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/documents/consent-sign/999999?template=fake.docx", json={
        "fisio_firma": "Test", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert res.status_code == 404


# --- Auto backup ---

def test_auto_backup_creates_daily_file():
    """auto_backup_db debe crear sante_diaria.db en la ruta configurada."""
    from app.reminders import auto_backup_db, DB_PATH
    tmp_dir = tempfile.mkdtemp()
    try:
        # get_auto_backup_path lee de Config/env; parcheamos para apuntar al tmp.
        with patch("app.storage.get_auto_backup_path", return_value=tmp_dir):
            created_dummy = False
            if not os.path.exists(DB_PATH):
                with open(DB_PATH, "wb") as f:
                    f.write(b"test")
                created_dummy = True
            auto_backup_db()
            assert os.path.exists(os.path.join(tmp_dir, "sante_diaria.db"))
            if created_dummy:
                os.unlink(DB_PATH)
    finally:
        shutil.rmtree(tmp_dir)


# --- Generador de plantillas (rellenado de marcadores) ---

def test_fill_consent_template_markers():
    """fill_consent_template reemplaza los marcadores y guarda en el output_dir dado."""
    from app.consent_generator import fill_consent_template, TEMPLATES_PATH

    data = {
        "nombre_paciente": "Juan Test",
        "dni_paciente": "11111111A",
        "nombre_tutor": "Maria Test",
        "dni_tutor": "22222222B",
        "relacion_tutor": "Madre",
        "fisio_firma": "Dr. Fisio",
        "dni_fisio_firma": "33333333C",
        "ud_fisioterapia": "Unidad Test",
        "patología_paciente": "Lumbalgia",
    }
    templates = [f for f in os.listdir(TEMPLATES_PATH) if f.endswith('.docx') and not f.startswith('~$')]
    assert len(templates) > 0

    out_dir = tempfile.mkdtemp()
    try:
        docx_path = fill_consent_template(templates[0], data, out_dir)
        assert os.path.exists(docx_path)
        from docx import Document
        doc = Document(docx_path)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Juan Test" in full_text
        assert "{{nombre_paciente}}" not in full_text
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


# --- Paciente sin campos de consentimiento antiguos ---

def test_patient_no_consent_fields(client, db):
    """El API de paciente no devuelve consent_signed ni consent_date."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get(f"/api/patients/{patient.id}", headers=headers)
    data = res.json()
    assert "consent_signed" not in data
    assert "consent_date" not in data
