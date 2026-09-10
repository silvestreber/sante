from tests.conftest import create_admin, login


def test_login_success(client, db):
    create_admin(db)
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    assert "token" in res.json()
    assert res.json()["role"] == "ADMIN"


def test_login_case_insensitive(client, db):
    create_admin(db)
    res = client.post("/api/auth/login", json={"username": "ADMIN", "password": "admin123"})
    assert res.status_code == 200


def test_login_wrong_password(client, db):
    create_admin(db)
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={"username": "noexiste", "password": "x"})
    assert res.status_code == 401


def test_protected_endpoint_no_token(client):
    res = client.get("/api/patients")
    assert res.status_code == 401


def test_protected_endpoint_invalid_token(client):
    res = client.get("/api/patients", headers={"Authorization": "Bearer invalid"})
    assert res.status_code == 401
