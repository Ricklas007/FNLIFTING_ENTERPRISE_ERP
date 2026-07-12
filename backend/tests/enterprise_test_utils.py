import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parents[1] / "data" / "test_fnlifting.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-more-than-thirty-two-chars")
os.environ.setdefault("BACKUP_ENCRYPTION_KEY", "test-backup-key-with-more-than-thirty-two-chars")

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.main import app
from app.models import Employee, User, UserMFAFactor, MFARecoveryCode, MFAChallenge
from seed import seed_database


def ensure_seeded() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        has_admin = db.scalar(select(User.id).where(User.email == "admin@fnlifting.com"))
    if not has_admin:
        seed_database()


def client() -> TestClient:
    ensure_seeded()
    return TestClient(app)


def login_headers(api: TestClient, identifier: str = "admin@fnlifting.com", password: str = "Admin@12345", portal: str = "staff") -> dict[str, str]:
    response = api.post("/api/v1/auth/login", json={"identifier": identifier, "password": password, "portal": portal, "remember_me": False})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "access_token" in payload, payload
    return {"Authorization": f"Bearer {payload['access_token']}"}


def reset_admin_mfa() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@fnlifting.com"))
        if not admin:
            return
        for model in (UserMFAFactor, MFARecoveryCode, MFAChallenge):
            for row in db.scalars(select(model).where(model.user_id == admin.id)):
                row.deleted_at = row.created_at
        db.commit()


def first_employee_id() -> str:
    with SessionLocal() as db:
        employee_id = db.scalar(select(Employee.id).where(Employee.deleted_at.is_(None)).limit(1))
        assert employee_id
        return employee_id
