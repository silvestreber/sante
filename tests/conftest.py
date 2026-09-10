import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Helpers ---

import bcrypt
from app.db.models import User, UserRole, Patient


def create_admin(db):
    pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    user = User(username="admin", password_hash=pw, full_name="Admin", role=UserRole.ADMIN, is_physio=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_physio(db):
    pw = bcrypt.hashpw("physio123".encode(), bcrypt.gensalt()).decode()
    user = User(username="physio", password_hash=pw, full_name="Fisio Test", role=UserRole.PHYSIO, is_physio=True, color="#ff0000")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_reception(db):
    pw = bcrypt.hashpw("recep123".encode(), bcrypt.gensalt()).decode()
    user = User(username="recep", password_hash=pw, full_name="Recepcion", role=UserRole.RECEPTION)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_patient(db):
    p = Patient(first_name="Ana", last_name="García", phone="600111222", email="ana@test.com", dni="12345678A")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def login(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {res.json()['token']}"}
