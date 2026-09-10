"""Tests for functionality not covered by existing test files."""
from datetime import datetime, timedelta
from tests.conftest import create_admin, create_patient, create_physio, create_reception, login


# === AUDIT ===

def test_audit_list_empty(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.get("/api/audit", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_audit_list_after_action(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    # Update patient triggers audit log
    client.put(f"/api/patients/{patient.id}", data={
        "first_name": "Ana", "last_name": "García", "phone": "600111222",
    }, headers=headers)
    res = client.get("/api/audit", headers=headers)
    assert res.json()["total"] >= 1


def test_audit_filter_by_action(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    client.put(f"/api/patients/{patient.id}", data={
        "first_name": "Ana", "last_name": "García", "phone": "600111222",
    }, headers=headers)
    res = client.get("/api/audit?action=EDITAR", headers=headers)
    assert res.json()["total"] >= 1
    res = client.get("/api/audit?action=NOEXISTE", headers=headers)
    assert res.json()["total"] == 0


def test_audit_requires_admin(client, db):
    create_admin(db)
    create_physio(db)
    headers = login(client, "physio", "physio123")
    res = client.get("/api/audit", headers=headers)
    assert res.status_code == 403


def test_audit_actions_list(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.get("/api/audit/actions", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_audit_entity_types_list(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.get("/api/audit/entity-types", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# === USERS (create, update, deactivate) ===

def test_create_user(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/users", json={
        "username": "nuevo", "password": "pass123",
        "full_name": "Nuevo User", "role": "RECEPTION",
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["id"] > 0


def test_create_user_duplicate(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/users", json={
        "username": "nuevo", "password": "pass123",
        "full_name": "Nuevo", "role": "RECEPTION",
    }, headers=headers)
    res = client.post("/api/users", json={
        "username": "nuevo", "password": "pass123",
        "full_name": "Otro", "role": "RECEPTION",
    }, headers=headers)
    assert res.status_code == 400


def test_update_user(client, db):
    create_admin(db)
    create_physio(db)
    headers = login(client, "admin", "admin123")
    users = client.get("/api/users", headers=headers).json()
    physio_user = next(u for u in users if u["username"] == "physio")
    res = client.put(f"/api/users/{physio_user['id']}", json={
        "full_name": "Fisio Actualizado",
    }, headers=headers)
    assert res.status_code == 200


def test_deactivate_user(client, db):
    create_admin(db)
    create_physio(db)
    headers = login(client, "admin", "admin123")
    users = client.get("/api/users", headers=headers).json()
    physio_user = next(u for u in users if u["username"] == "physio")
    res = client.patch(f"/api/users/{physio_user['id']}/deactivate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_deactivate_self_fails(client, db):
    admin = create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.patch(f"/api/users/{admin.id}/deactivate", headers=headers)
    assert res.status_code == 400


# === WAITLIST (resolve, check-slot, patient pending, delete patient entries) ===

def test_resolve_waitlist_entry(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "ANY",
    }, headers=headers)
    entry_id = res.json()["id"]
    res = client.put(f"/api/waitlist/{entry_id}/resolve", headers=headers)
    assert res.status_code == 200
    # Should not appear in list (resolved)
    res = client.get("/api/waitlist", headers=headers)
    assert all(e["id"] != entry_id for e in res.json())


def test_waitlist_patient_pending(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.get(f"/api/waitlist/patient/{patient.id}/pending", headers=headers)
    assert res.json()["count"] == 0
    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "MORNING",
    }, headers=headers)
    res = client.get(f"/api/waitlist/patient/{patient.id}/pending", headers=headers)
    assert res.json()["count"] == 1


def test_waitlist_delete_patient_entries(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "ANY",
    }, headers=headers)
    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "MORNING",
    }, headers=headers)
    res = client.delete(f"/api/waitlist/patient/{patient.id}", headers=headers)
    assert res.status_code == 200
    res = client.get(f"/api/waitlist/patient/{patient.id}/pending", headers=headers)
    assert res.json()["count"] == 0


def test_waitlist_check_slot(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "MORNING",
        "physio_ids": [physio.id],
    }, headers=headers)
    # Morning slot should match
    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).isoformat()
    res = client.get(f"/api/waitlist/check-slot?start_time={start}&physio_id={physio.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_waitlist_check_slot_no_match(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/waitlist", json={
        "patient_id": patient.id, "time_preference": "MORNING",
    }, headers=headers)
    # Afternoon slot should NOT match morning preference
    start = (datetime.now() + timedelta(days=1)).replace(hour=16, minute=0).isoformat()
    res = client.get(f"/api/waitlist/check-slot?start_time={start}&physio_id={physio.id}", headers=headers)
    assert len(res.json()) == 0


# === NOTIFICATIONS (mark read, mark all read, delete) ===

def test_mark_notification_read(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    admin_headers = login(client, "admin", "admin123")
    client.post("/api/notifications", json={
        "recipient_id": physio.id, "message": "Test",
    }, headers=admin_headers)

    physio_headers = login(client, "physio", "physio123")
    notifs = client.get("/api/notifications", headers=physio_headers).json()
    nid = notifs[0]["id"]
    res = client.put(f"/api/notifications/{nid}/read", headers=physio_headers)
    assert res.status_code == 200
    res = client.get("/api/notifications/unread-count", headers=physio_headers)
    assert res.json()["count"] == 0


def test_mark_all_notifications_read(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    admin_headers = login(client, "admin", "admin123")
    client.post("/api/notifications", json={"recipient_id": physio.id, "message": "A"}, headers=admin_headers)
    client.post("/api/notifications", json={"recipient_id": physio.id, "message": "B"}, headers=admin_headers)

    physio_headers = login(client, "physio", "physio123")
    res = client.put("/api/notifications/read-all", headers=physio_headers)
    assert res.status_code == 200
    res = client.get("/api/notifications/unread-count", headers=physio_headers)
    assert res.json()["count"] == 0


def test_delete_notification(client, db):
    admin = create_admin(db)
    physio = create_physio(db)
    admin_headers = login(client, "admin", "admin123")
    client.post("/api/notifications", json={"recipient_id": physio.id, "message": "Del"}, headers=admin_headers)

    physio_headers = login(client, "physio", "physio123")
    notifs = client.get("/api/notifications", headers=physio_headers).json()
    nid = notifs[0]["id"]
    res = client.delete(f"/api/notifications/{nid}", headers=physio_headers)
    assert res.status_code == 200
    notifs = client.get("/api/notifications", headers=physio_headers).json()
    assert len(notifs) == 0


# === TREATMENTS (get, update, delete) ===

def test_get_treatment(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/treatments", json={
        "patient_id": patient.id, "title": "Ejercicios",
        "description": "Desc",
    }, headers=headers)
    tid = res.json()["id"]
    res = client.get(f"/api/treatments/{tid}", headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Ejercicios"


def test_update_treatment(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/treatments", json={
        "patient_id": patient.id, "title": "Original",
        "description": "Desc",
    }, headers=headers)
    tid = res.json()["id"]
    res = client.put(f"/api/treatments/{tid}", json={"title": "Modificado"}, headers=headers)
    assert res.status_code == 200
    res = client.get(f"/api/treatments/{tid}", headers=headers)
    assert res.json()["title"] == "Modificado"


def test_delete_treatment(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/treatments", json={
        "patient_id": patient.id, "title": "Borrar",
        "description": "Desc",
    }, headers=headers)
    tid = res.json()["id"]
    res = client.delete(f"/api/treatments/{tid}", headers=headers)
    assert res.status_code == 200
    res = client.get(f"/api/treatments/{tid}", headers=headers)
    assert res.status_code == 404


# === CLINICAL (update session) ===

def test_update_clinical_session(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)

    admin_headers = login(client, "admin", "admin123")
    start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0).strftime("%Y-%m-%dT%H:%M")
    res = client.post("/api/appointments", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start, "duration_minutes": 45, "location": "CLINIC", "force": True,
    }, headers=admin_headers)
    apt_id = res.json()["id"]

    physio_headers = login(client, "physio", "physio123")
    res = client.post("/api/clinical/sessions", json={
        "patient_id": patient.id, "appointment_id": apt_id, "observations": "Inicial",
    }, headers=physio_headers)
    session_id = res.json()["id"]

    res = client.put(f"/api/clinical/sessions/{session_id}", json={
        "observations": "Actualizado",
    }, headers=physio_headers)
    assert res.status_code == 200

    res = client.get(f"/api/clinical/patient/{patient.id}", headers=physio_headers)
    assert res.json()["sessions"][0]["observations"] == "Actualizado"


# === FINANCE (list entries, update entry, delete entry) ===

def test_list_finance_entries(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/finance/entries", json={
        "entry_type": "EXPENSE", "amount": 50.0,
        "description": "Material", "date": "2025-01-15",
    }, headers=headers)
    res = client.get("/api/finance/entries?start=2025-01-01&end=2025-01-31", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_update_finance_entry(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/finance/entries", json={
        "entry_type": "EXPENSE", "amount": 50.0,
        "description": "Material", "date": "2025-01-15",
    }, headers=headers)
    eid = res.json()["id"]
    res = client.put(f"/api/finance/entries/{eid}", json={"amount": 75.0}, headers=headers)
    assert res.status_code == 200
    entries = client.get("/api/finance/entries?start=2025-01-01&end=2025-01-31", headers=headers).json()
    assert entries[0]["amount"] == 75.0


def test_delete_finance_entry(client, db):
    create_admin(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/finance/entries", json={
        "entry_type": "EXPENSE", "amount": 50.0,
        "description": "Borrar", "date": "2025-01-15",
    }, headers=headers)
    eid = res.json()["id"]
    res = client.delete(f"/api/finance/entries/{eid}", headers=headers)
    assert res.status_code == 200
    entries = client.get("/api/finance/entries?start=2025-01-01&end=2025-01-31", headers=headers).json()
    assert len(entries) == 0


# === PATIENTS (deactivate/toggle) ===

def test_deactivate_patient(client, db):
    create_admin(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")
    res = client.patch(f"/api/patients/{patient.id}/deactivate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    # Toggle back
    res = client.patch(f"/api/patients/{patient.id}/deactivate", headers=headers)
    assert res.json()["is_active"] is True


def test_deactivate_patient_requires_role(client, db):
    create_admin(db)
    create_physio(db)
    patient = create_patient(db)
    headers = login(client, "physio", "physio123")
    res = client.patch(f"/api/patients/{patient.id}/deactivate", headers=headers)
    assert res.status_code == 403


# === APPOINTMENTS (recurrence) ===

def test_create_recurrence(client, db):
    create_admin(db)
    physio = create_physio(db)
    patient = create_patient(db)
    headers = login(client, "admin", "admin123")

    start = (datetime.now() + timedelta(days=7)).replace(hour=10, minute=0)
    # Adjust to Monday
    start = start - timedelta(days=start.weekday())
    start_str = start.strftime("%Y-%m-%dT%H:%M")

    res = client.post("/api/appointments/recurrence", json={
        "patient_id": patient.id, "physio_id": physio.id,
        "start_time": start_str, "duration_minutes": 45,
        "location": "CLINIC", "days_of_week": [0, 2], "weeks": 2,
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["created"] >= 2


# === PHYSIO ABSENCES ===

def test_create_physio_absence(client, db):
    create_admin(db)
    physio = create_physio(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/config/physio-absences", json={
        "user_id": physio.id, "date_from": "2025-06-01", "date_to": "2025-06-05",
        "reason": "Vacaciones",
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["id"] > 0


def test_create_physio_absence_partial_day(client, db):
    create_admin(db)
    physio = create_physio(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/config/physio-absences", json={
        "user_id": physio.id, "date_from": "2025-06-10", "date_to": "2025-06-10",
        "time_from": "09:00", "time_to": "12:00", "reason": "Médico",
    }, headers=headers)
    assert res.status_code == 201


def test_list_physio_absences(client, db):
    create_admin(db)
    physio = create_physio(db)
    headers = login(client, "admin", "admin123")
    client.post("/api/config/physio-absences", json={
        "user_id": physio.id, "date_from": "2025-07-01", "date_to": "2025-07-15",
    }, headers=headers)
    res = client.get(f"/api/config/physio-absences/{physio.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["date_from"] == "2025-07-01"


def test_delete_physio_absence(client, db):
    create_admin(db)
    physio = create_physio(db)
    headers = login(client, "admin", "admin123")
    res = client.post("/api/config/physio-absences", json={
        "user_id": physio.id, "date_from": "2025-08-01", "date_to": "2025-08-01",
    }, headers=headers)
    aid = res.json()["id"]
    res = client.delete(f"/api/config/physio-absences/{aid}", headers=headers)
    assert res.status_code == 200
    res = client.get(f"/api/config/physio-absences/{physio.id}", headers=headers)
    assert len(res.json()) == 0
