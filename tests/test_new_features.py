"""Tests for new features: consents, backup, income management."""
import os
from tests.conftest import create_admin, create_patient, create_physio, login
from app.db.models import FinanceEntry, EntryType, Invoice


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


def test_sign_consent(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Find a template
    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Maria Rodriguez",
        "dni_fisio_firma": "11111111A",
        "ud_fisioterapia": "Clinica Test",
        "nombre_tutor": None,
        "relacion_tutor": None,
        "dni_tutor": None,
        "observaciones": "Test",
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] > 0
    assert "pdf_path" in data
    # Cleanup generated file
    if os.path.exists(data["pdf_path"]):
        os.unlink(data["pdf_path"])


def test_sign_consent_with_tutor(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Maria Rodriguez",
        "dni_fisio_firma": "11111111A",
        "ud_fisioterapia": "Clinica Test",
        "nombre_tutor": "Pedro Garcia",
        "relacion_tutor": "Padre",
        "dni_tutor": "22222222B",
        "observaciones": "",
    }, headers=headers)
    assert res.status_code == 200
    # Cleanup
    if os.path.exists(res.json()["pdf_path"]):
        os.unlink(res.json()["pdf_path"])


def test_sign_consent_patient_not_found(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/documents/consent-sign/9999?template=fake.docx", json={
        "fisio_firma": "Test", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert res.status_code == 404


def test_sign_consent_template_not_found(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post(f"/api/documents/consent-sign/{patient.id}?template=NO_EXISTE.docx", json={
        "fisio_firma": "Test", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    assert res.status_code == 404


def test_list_signed_consents(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Sign one
    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]
    sign_res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Test Fisio", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    pdf_path = sign_res.json()["pdf_path"]

    # List
    res = client.get(f"/api/documents/signed-consents/{patient.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["template_name"] == template.replace(".docx", "")

    # Cleanup
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


def test_multiple_consents_per_patient(client, db):
    """A patient can sign multiple consents."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    templates = res.json()
    paths = []

    for t in templates[:2]:  # Sign up to 2 different templates
        r = client.post(f"/api/documents/consent-sign/{patient.id}?template={t['filename']}", json={
            "fisio_firma": "Fisio", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
        }, headers=headers)
        assert r.status_code == 200
        paths.append(r.json()["pdf_path"])

    res = client.get(f"/api/documents/signed-consents/{patient.id}", headers=headers)
    assert len(res.json()) == min(2, len(templates))

    # Cleanup
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def test_view_signed_consent_pdf(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/documents/consent-templates", headers=headers)
    template = res.json()[0]["filename"]
    sign_res = client.post(f"/api/documents/consent-sign/{patient.id}?template={template}", json={
        "fisio_firma": "Fisio", "dni_fisio_firma": "X", "ud_fisioterapia": "X",
    }, headers=headers)
    consent_id = sign_res.json()["id"]
    pdf_path = sign_res.json()["pdf_path"]

    res = client.get(f"/api/documents/signed-consents/{patient.id}/{consent_id}/pdf", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"

    # Cleanup
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


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
