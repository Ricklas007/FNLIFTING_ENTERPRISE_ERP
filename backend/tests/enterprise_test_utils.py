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
from app.models import Asset, Client, Department, Driver, Employee, Equipment, EquipmentType, TechnicalSignatory, Truck, User, UserMFAFactor, MFARecoveryCode, MFAChallenge
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


def first_department_id() -> str:
    with SessionLocal() as db:
        department_id = db.scalar(select(Department.id).where(Department.deleted_at.is_(None)).limit(1))
        assert department_id
        return department_id


def first_client_id() -> str:
    with SessionLocal() as db:
        client_id = db.scalar(select(Client.id).where(Client.deleted_at.is_(None)).limit(1))
        assert client_id
        return client_id


def first_equipment_type_id() -> str:
    with SessionLocal() as db:
        type_id = db.scalar(select(EquipmentType.id).where(EquipmentType.deleted_at.is_(None)).limit(1))
        assert type_id
        return type_id


def first_equipment_id() -> str:
    with SessionLocal() as db:
        equipment_id = db.scalar(select(Equipment.id).where(Equipment.deleted_at.is_(None)).limit(1))
        assert equipment_id
        return equipment_id


def first_asset_id() -> str:
    with SessionLocal() as db:
        asset_id = db.scalar(select(Asset.id).where(Asset.deleted_at.is_(None)).limit(1))
        assert asset_id
        return asset_id


def first_driver_id() -> str:
    with SessionLocal() as db:
        driver_id = db.scalar(select(Driver.id).where(Driver.deleted_at.is_(None)).limit(1))
        assert driver_id
        return driver_id


def first_truck_id() -> str:
    with SessionLocal() as db:
        truck_id = db.scalar(select(Truck.id).where(Truck.deleted_at.is_(None)).limit(1))
        assert truck_id
        return truck_id


def first_approver_signatory_id() -> str:
    with SessionLocal() as db:
        signatory_id = db.scalar(select(TechnicalSignatory.id).where(TechnicalSignatory.can_approve.is_(True), TechnicalSignatory.deleted_at.is_(None)).limit(1))
        assert signatory_id
        return signatory_id
