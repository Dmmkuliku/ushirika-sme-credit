import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-32chars"
os.environ["PSEUDONYMIZATION_KEY"] = "test-pseudo-key-for-unit-tests-32"
os.environ["APP_ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["MODEL_DIR"] = tempfile.mkdtemp()

from app.database import Base, get_db
from app.main import app
from app.services.ml_training import train_models

train_models(db_session=None)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_sme(client: TestClient, nida: str = "19900101123456789012") -> dict:
    date_of_birth = f"{nida[:4]}-{nida[4:6]}-{nida[6:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "nida": nida,
            "phone": "+255712345678",
            "full_name": "Test Business Ltd",
            "location": "Dar es Salaam",
            "district": "Ilala",
            "business_type": "Retailer",
            "gender": "Male",
            "nationality": "Tanzanian",
            "date_of_birth": date_of_birth,
            "tin": "123456789",
            "pin": "1234",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def create_admin(client: TestClient, db) -> str:
    from app.models import User, UserRole
    from app.utils.security import hash_pin

    admin = User(
        login_id="ADMIN001",
        hashed_pin=hash_pin("1234"),
        role=UserRole.ADMIN,
        full_name="Test Admin",
        gender="Male",
    )
    db.add(admin)
    db.commit()
    resp = client.post("/api/auth/login", json={"login_id": "ADMIN001", "pin": "1234"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def create_lender_via_admin(client: TestClient, db, membership_number: str = "EMP001") -> str:
    admin_token = create_admin(client, db)
    resp = client.post(
        "/api/admin/accounts/lender",
        json={
            "membership_number": membership_number,
            "full_name": "Test Lender",
            "gender": "Male",
            "organization": "CRDB",
            "work_email": "lender@crdb.co.tz",
            "pin": "1234",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    login_resp = client.post("/api/auth/login", json={"login_id": membership_number, "pin": "1234"})
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def login(client: TestClient, login_id: str, pin: str = "1234") -> str:
    resp = client.post("/api/auth/login", json={"login_id": login_id, "pin": pin})
    assert resp.status_code == 200
    return resp.json()["access_token"]
