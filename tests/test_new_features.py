"""Tests for new features: consents, backup, income management."""
import os
import shutil
import sys

import pytest

from tests.conftest import create_admin, create_patient, create_physio, login
from app.db.models import FinanceEntry, EntryType, Invoice


def _conversion_available() -> bool:
    if sys.platform.startswith("win"):
        return False  # docx2pdf/Word no disponible en el entorno de test Windows
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


# --- Consent Templates ---

def test_list_consent_templates(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    assert res.status_code == 200
    templates = res.json()
    assert isinstance(templates, list)
    # Should find at least the CI FISIOTERAPIA GENERAL.docx
    names = [t["filename"] for t in templates]
    assert any("FISIOTERAPIA GENERAL" in n for n in names)


@pytest.mark.skipif(not _conversion_available(), reason="Conversión docx->pdf no disponible")
def test_sign_consent_creates_document(client, db):
    """Firmar crea un documento (PatientDocument) que aparece en la lista del paciente."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Maria Rodriguez",
        "dni_fisio_firma": "11111111A",
        "ud_fisioterapia": "Clinica Test",
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] > 0

    docs = client.get(f"/api/patients/{patient.id}/documents", headers=headers).json()
    assert len(docs) == 1


@pytest.mark.skipif(not _conversion_available(), reason="Conversión docx->pdf no disponible")
def test_sign_revocation_creates_document(client, db):
    """Generar una revocación crea un documento independiente."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "is_revocacion": True,
        "nombre_revocante": "Ana García",
        "observaciones_revoc": "Motivo test",
    }, headers=headers)
    assert res.status_code == 200
    assert "Revocación" in res.json()["filename"]


def test_sign_consent_patient_not_found(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/documents/consent-sign/9999?template=fake.docx", json={
        "fisio_firma": "Test", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert res.status_code == 404


@pytest.mark.skipif(not _conversion_available(), reason="Conversión docx->pdf no disponible")
def test_sign_consent_template_not_found(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template=NO_EXISTE.docx", json={
        "fisio_firma": "Test", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert res.status_code == 404


# --- Backup ---

def test_backup_export(client, db):
    admin = create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/backup/export", json={"password": "admin123"}, headers=headers)
    assert res.status_code == 200
    assert "application/octet-stream" in res.headers.get("content-type", "")


def test_backup_export_wrong_password(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/backup/export", json={"password": "wrong"}, headers=headers)
    assert res.status_code == 403


def test_backup_export_requires_admin(client, db):
    create_admin(db)
    create_physio(db)
    headers = login(client, "physio", "physio123")

    res = client.post("/api/backup/export", json={"password": "physio123"}, headers=headers)
    assert res.status_code == 403


# --- Income management ---

def test_mark_paid_creates_income(client, db):
    """Marking an unpaid invoice as paid should create an income entry."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Create unpaid invoice
    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 45.0,
    }, headers=headers)
    inv_id = res.json()["id"]

    # No income yet
    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 0

    # Mark as paid
    client.put(f"/api/billing/invoices/{inv_id}", json={
        "payment_method": "CASH", "is_paid": True,
    }, headers=headers)

    db.expire_all()
    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 1
    assert entries[0].amount == 45.0


def test_unmark_paid_removes_income(client, db):
    """Unmarking a paid invoice should remove the income entry."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Create paid invoice
    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 50.0,
        "payment_method": "BIZUM", "is_paid": True,
    }, headers=headers)
    inv_id = res.json()["id"]

    db.expire_all()
    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 1

    # Unmark as paid
    client.put(f"/api/billing/invoices/{inv_id}", json={"is_paid": False}, headers=headers)

    db.expire_all()
    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 0


def test_update_amount_updates_income(client, db):
    """Changing amount on a paid invoice should update the income entry."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 40.0,
        "payment_method": "CASH", "is_paid": True,
    }, headers=headers)
    inv_id = res.json()["id"]

    # Update amount
    client.put(f"/api/billing/invoices/{inv_id}", json={"amount": 60.0, "is_paid": True}, headers=headers)

    db.expire_all()
    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 1
    assert entries[0].amount == 60.0


def test_delete_paid_invoice_removes_income(client, db):
    """Deleting a paid invoice should remove the income entry."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 35.0,
        "payment_method": "CASH", "is_paid": True,
    }, headers=headers)
    inv_id = res.json()["id"]

    db.expire_all()
    assert db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).count() == 1

    client.delete(f"/api/billing/invoices/{inv_id}", headers=headers)

    db.expire_all()
    assert db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).count() == 0


# --- Invoice full edit ---

def test_edit_invoice_doc_type(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 30.0,
    }, headers=headers)
    inv_id = res.json()["id"]

    res = client.put(f"/api/billing/invoices/{inv_id}", json={
        "doc_type": "INVOICE", "amount": 30.0,
    }, headers=headers)
    assert res.status_code == 200

    invoices = client.get(f"/api/billing/invoices/patient/{patient.id}", headers=headers).json()
    inv = next(i for i in invoices if i["id"] == inv_id)
    assert inv["doc_type"] == "INVOICE"


def test_edit_invoice_clear_appointment(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    from datetime import datetime, timedelta
    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    apt_res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=headers)
    apt_id = apt_res.json()["id"]

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 45.0,
        "appointment_id": apt_id,
    }, headers=headers)
    inv_id = res.json()["id"]

    # Clear appointment
    res = client.put(f"/api/billing/invoices/{inv_id}", json={
        "clear_appointment": True,
    }, headers=headers)
    assert res.status_code == 200

    invoices = client.get(f"/api/billing/invoices/patient/{patient.id}", headers=headers).json()
    inv = next(i for i in invoices if i["id"] == inv_id)
    assert inv["appointment_id"] is None
