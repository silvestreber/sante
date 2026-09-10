from tests.conftest import create_admin, create_patient, create_physio, login
from app.db.models import Appointment, FinanceEntry, EntryType
from datetime import datetime, timezone


def test_create_invoice_receipt(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 45.0,
        "payment_method": "CASH", "is_paid": True,
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["invoice_number"].startswith("J-")


def test_create_invoice_factura(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 50.0,
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["invoice_number"].startswith("F-")


def test_create_invoice_simplified(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "SIMPLIFIED_INVOICE", "amount": 30.0,
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["invoice_number"].startswith("FS-")


def test_sequential_numbering(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    r1 = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 10.0,
    }, headers=headers)
    r2 = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 20.0,
    }, headers=headers)
    seq1 = int(r1.json()["invoice_number"].rsplit("-", 1)[1])
    seq2 = int(r2.json()["invoice_number"].rsplit("-", 1)[1])
    assert seq2 == seq1 + 1


def test_list_invoices(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 50.0,
    }, headers=headers)
    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 25.0,
    }, headers=headers)

    res = client.get(f"/api/billing/invoices/patient/{patient.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_update_invoice(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 40.0,
    }, headers=headers)
    inv_id = res.json()["id"]

    res = client.put(f"/api/billing/invoices/{inv_id}", json={
        "amount": 55.0, "payment_method": "BIZUM", "is_paid": True,
    }, headers=headers)
    assert res.status_code == 200

    invoices = client.get(f"/api/billing/invoices/patient/{patient.id}", headers=headers).json()
    inv = next(i for i in invoices if i["id"] == inv_id)
    assert inv["amount"] == 55.0
    assert inv["payment_method"] == "BIZUM"
    assert inv["is_paid"] is True


def test_delete_invoice(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 30.0,
    }, headers=headers)
    inv_id = res.json()["id"]

    res = client.delete(f"/api/billing/invoices/{inv_id}", headers=headers)
    assert res.status_code == 200

    invoices = client.get(f"/api/billing/invoices/patient/{patient.id}", headers=headers).json()
    assert len(invoices) == 0


def test_paid_invoice_creates_income(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 45.0,
        "payment_method": "CASH", "is_paid": True,
    }, headers=headers)

    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 1
    assert entries[0].amount == 45.0


def test_pack_payment_no_income(client, db):
    """Paying with pack should NOT create income (income was at pack purchase)."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Create pack
    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 200.0, "expires_at": "2027-12-31",
    }, headers=headers)
    pack_id = res.json()["id"]

    # Create invoice paid with pack (no payment_method)
    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "RECEIPT", "amount": 0,
        "session_pack_id": pack_id, "is_paid": True,
    }, headers=headers)

    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert len(entries) == 0


def test_pending_payments(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "doc_type": "INVOICE", "amount": 60.0,
    }, headers=headers)

    res = client.get("/api/billing/pending", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["pending_amount"] == 60.0


# --- Session Packs ---

def test_create_pack(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 200.0, "expires_at": "2027-12-31",
    }, headers=headers)
    assert res.status_code == 201


def test_consume_session(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 3, "price": 120.0, "expires_at": "2027-12-31",
    }, headers=headers)
    pack_id = res.json()["id"]

    res = client.post(f"/api/billing/packs/{pack_id}/consume", headers=headers)
    assert res.json()["remaining"] == 2


def test_consume_exhausted_pack(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 1, "price": 40.0, "expires_at": "2027-12-31",
    }, headers=headers)
    pack_id = res.json()["id"]

    client.post(f"/api/billing/packs/{pack_id}/consume", headers=headers)
    res = client.post(f"/api/billing/packs/{pack_id}/consume", headers=headers)
    assert res.status_code == 400


def test_consume_expired_pack(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 200.0, "expires_at": "2020-01-01",
    }, headers=headers)
    pack_id = res.json()["id"]

    res = client.post(f"/api/billing/packs/{pack_id}/consume", headers=headers)
    assert res.status_code == 400


def test_update_pack_updates_income(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    # Create pack and pay for it
    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 200.0, "expires_at": "2027-12-31",
    }, headers=headers)
    pack_id = res.json()["id"]

    client.post("/api/billing/invoices", json={
        "patient_id": patient.id, "session_pack_id": pack_id,
        "doc_type": "RECEIPT", "amount": 200.0, "payment_method": "CASH", "is_paid": True,
    }, headers=headers)

    # Update pack price
    client.put(f"/api/billing/packs/{pack_id}", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 250.0, "expires_at": "2027-12-31",
    }, headers=headers)

    entries = db.query(FinanceEntry).filter(FinanceEntry.entry_type == EntryType.INCOME).all()
    assert entries[0].amount == 250.0


def test_cancel_pack(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/billing/packs", json={
        "patient_id": patient.id, "total_sessions": 5, "price": 200.0, "expires_at": "2027-12-31",
    }, headers=headers)
    pack_id = res.json()["id"]

    res = client.delete(f"/api/billing/packs/{pack_id}", headers=headers)
    assert res.status_code == 200

    packs = client.get(f"/api/billing/packs/patient/{patient.id}", headers=headers).json()
    assert packs[0]["is_cancelled"] is True
