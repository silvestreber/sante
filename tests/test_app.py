from tests.conftest import create_admin, create_patient, create_physio, login
from datetime import datetime, timedelta


# --- Patients ---

def test_create_patient(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    from io import BytesIO
    res = client.post("/api/patients", data={
        "first_name": "Juan", "last_name": "López", "phone": "600222333",
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["id"] > 0


def test_list_patients(client, db):
    create_admin(db)
    create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/patients", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_search_patients(client, db):
    create_admin(db)
    create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/patients?q=Ana", headers=headers)
    assert res.json()["total"] == 1

    res = client.get("/api/patients?q=noexiste", headers=headers)
    assert res.json()["total"] == 0


def test_get_patient(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get(f"/api/patients/{patient.id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["first_name"] == "Ana"


def test_update_patient(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.put(f"/api/patients/{patient.id}", data={
        "first_name": "Ana María", "last_name": "García", "phone": "600111222",
    }, headers=headers)
    assert res.status_code == 200

    res = client.get(f"/api/patients/{patient.id}", headers=headers)
    assert res.json()["first_name"] == "Ana María"


def test_create_patient_with_clinical_fields(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/patients", data={
        "first_name": "Pedro", "last_name": "Ruiz", "phone": "611222333",
        "motivo_consulta": "Dolor lumbar crónico",
        "anamnesis": "Patologías músculo-esqueléticas: Lumbalgia\nOtras patologías: Ninguna",
        "tratamiento_contraindicaciones": "Tratamiento: Fisioterapia manual\nContraindicaciones: Ninguna",
    }, headers=headers)
    assert res.status_code == 201
    pid = res.json()["id"]

    res = client.get(f"/api/patients/{pid}", headers=headers)
    data = res.json()
    assert data["motivo_consulta"] == "Dolor lumbar crónico"
    assert "Lumbalgia" in data["anamnesis"]
    assert "Fisioterapia manual" in data["tratamiento_contraindicaciones"]


def test_update_patient_clinical_fields(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.put(f"/api/patients/{patient.id}", data={
        "first_name": "Ana", "last_name": "García", "phone": "600111222",
        "motivo_consulta": "Cervicalgia",
        "anamnesis": "Profesión: Administrativo",
        "tratamiento_contraindicaciones": "Tratamiento: Masaje\nContraindicaciones: Marcapasos",
    }, headers=headers)
    assert res.status_code == 200

    res = client.get(f"/api/patients/{patient.id}", headers=headers)
    data = res.json()
    assert data["motivo_consulta"] == "Cervicalgia"
    assert "Administrativo" in data["anamnesis"]
    assert "Marcapasos" in data["tratamiento_contraindicaciones"]


def test_patient_clinical_fields_optional(client, db):
    """Los campos clínicos son opcionales — crear paciente sin ellos sigue funcionando."""
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/patients", data={
        "first_name": "Luis", "last_name": "Martín", "phone": "699000111",
    }, headers=headers)
    assert res.status_code == 201
    pid = res.json()["id"]

    res = client.get(f"/api/patients/{pid}", headers=headers)
    data = res.json()
    assert data["motivo_consulta"] is None
    assert data["anamnesis"] is None
    assert data["tratamiento_contraindicaciones"] is None


def test_patient_get_returns_clinical_fields(client, db):
    """El endpoint GET incluye los tres campos clínicos en la respuesta."""
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.get(f"/api/patients/{patient.id}", headers=headers)
    data = res.json()
    assert "motivo_consulta" in data
    assert "anamnesis" in data
    assert "tratamiento_contraindicaciones" in data


# --- Appointments ---

def test_create_appointment(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=headers)
    assert res.status_code == 201


def test_list_appointments(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0)
    start_str = start.strftime("%Y-%m-%dT%H:%M")
    client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start_str, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=headers)

    range_start = (start - timedelta(days=1)).isoformat()
    range_end = (start + timedelta(days=1)).isoformat()
    res = client.get(f"/api/appointments?start={range_start}&end={range_end}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_update_appointment(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=headers)
    apt_id = res.json()["id"]

    res = client.put(f"/api/appointments/{apt_id}", json={
        "status": "CONFIRMED", "notes": "Test note",
    }, headers=headers)
    assert res.status_code == 200


def test_cancel_appointment(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=headers)
    apt_id = res.json()["id"]

    res = client.delete(f"/api/appointments/{apt_id}", headers=headers)
    assert res.status_code == 200


# --- Clinical Sessions ---

def test_create_clinical_session(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "physio", "physio123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    admin_headers = login(client, "admin", "admin123")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=admin_headers)
    apt_id = res.json()["id"]

    res = client.post("/api/clinical/sessions", json={
        "patient_id": patient.id, "appointment_id": apt_id, "observations": "Todo bien",
    }, headers=headers)
    assert res.status_code == 201


def test_get_clinical_history(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "physio", "physio123")

    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    admin_headers = login(client, "admin", "admin123")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=admin_headers)
    apt_id = res.json()["id"]

    client.post("/api/clinical/sessions", json={
        "patient_id": patient.id, "appointment_id": apt_id, "observations": "Sesión 1",
    }, headers=headers)

    res = client.get(f"/api/clinical/patient/{patient.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["sessions"]) == 1


def test_clinical_session_uses_appointment_date(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)

    start = (datetime.now() + timedelta(days=5)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    admin_headers = login(client, "admin", "admin123")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=admin_headers)
    apt_id = res.json()["id"]

    headers = login(client, "physio", "physio123")
    client.post("/api/clinical/sessions", json={
        "patient_id": patient.id, "appointment_id": apt_id,
    }, headers=headers)

    res = client.get(f"/api/clinical/patient/{patient.id}", headers=headers)
    session_date = res.json()["sessions"][0]["date"]
    assert start[:10] in session_date


# --- Config ---

def test_get_settings(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/config/settings", headers=headers)
    assert res.status_code == 200
    assert "default_duration" in res.json()
    assert "default_session_price" in res.json()
    assert "default_pack_price" in res.json()


def test_update_settings(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.put("/api/config/settings", json={
        "default_duration": 60, "default_session_price": 45.0, "default_pack_price": 200.0,
    }, headers=headers)
    assert res.status_code == 200

    res = client.get("/api/config/settings", headers=headers)
    data = res.json()
    assert data["default_duration"] == 60
    assert data["default_session_price"] == 45.0
    assert data["default_pack_price"] == 200.0


# --- Notifications ---

def test_create_notification(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/notifications", json={
        "recipient_id": physio.id, "message": "Paciente llega tarde",
    }, headers=headers)
    assert res.status_code == 201


def test_list_notifications(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    admin_headers = login(client, "admin", "admin123")

    client.post("/api/notifications", json={
        "recipient_id": physio.id, "message": "Test",
    }, headers=admin_headers)

    physio_headers = login(client, "physio", "physio123")
    res = client.get("/api/notifications", headers=physio_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_unread_count(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    admin_headers = login(client, "admin", "admin123")

    client.post("/api/notifications", json={
        "recipient_id": physio.id, "message": "Aviso 1",
    }, headers=admin_headers)
    client.post("/api/notifications", json={
        "recipient_id": physio.id, "message": "Aviso 2",
    }, headers=admin_headers)

    physio_headers = login(client, "physio", "physio123")
    res = client.get("/api/notifications/unread-count", headers=physio_headers)
    assert res.json()["count"] == 2


# --- Treatments ---

def test_create_treatment(client, db):
    admin = create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/treatments", json={
        "patient_id": patient.id, "title": "Ejercicios lumbares",
        "description": "Hacer 3 series de 10 repeticiones",
    }, headers=headers)
    assert res.status_code == 201


def test_list_treatments(client, db):
    admin = create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/treatments", json={
        "patient_id": patient.id, "title": "Ejercicios",
        "description": "Descripción",
    }, headers=headers)

    res = client.get(f"/api/treatments/patient/{patient.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


# --- Finance ---

def test_create_finance_entry(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/finance/entries", json={
        "entry_type": "EXPENSE", "amount": 100.0,
        "description": "Material", "date": "2025-01-15",
    }, headers=headers)
    assert res.status_code == 201


def test_finance_balance(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/finance/entries", json={
        "entry_type": "INCOME", "amount": 500.0, "description": "Cobro", "date": "2025-01-10",
    }, headers=headers)
    client.post("/api/finance/entries", json={
        "entry_type": "EXPENSE", "amount": 100.0, "description": "Gasto", "date": "2025-01-12",
    }, headers=headers)

    res = client.get("/api/finance/balance?start=2025-01-01&end=2025-01-31", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["income"] == 500.0
    assert data["expense"] == 100.0
    assert data["balance"] == 400.0


def test_finance_requires_admin(client, db):
    create_admin(db)
    create_physio(db)
    headers = login(client, "physio", "physio123")

    res = client.get("/api/finance/balance?start=2025-01-01&end=2025-01-31", headers=headers)
    assert res.status_code == 403


# --- Users ---

def test_list_users(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.get("/api/users", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


# --- Waitlist ---

def test_add_to_waitlist(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "ANY", "asap": True,
    }, headers=headers)
    assert res.status_code == 201


def test_list_waitlist(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "MORNING", "priority": True,
    }, headers=headers)

    res = client.get("/api/waitlist", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["priority"] is True


def test_delete_waitlist_entry(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    res = client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "ANY",
    }, headers=headers)
    entry_id = res.json()["id"]

    res = client.delete(f"/api/waitlist/{entry_id}", headers=headers)
    assert res.status_code == 200


# --- Notes API ---

def test_notes_read_write(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")

    res = client.put("/api/notes", json={"content": "Test note content"}, headers=headers)
    assert res.status_code == 200

    res = client.get("/api/notes", headers=headers)
    assert "Test note content" in res.json()["content"]
