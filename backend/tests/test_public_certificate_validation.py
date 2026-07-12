from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Certificate
from tests.enterprise_test_utils import client


def test_public_certificate_validation_hash_and_no_sensitive_fields():
    api = client()
    with SessionLocal() as db:
        token = db.scalar(select(Certificate.qr_token).where(Certificate.status == "issued", Certificate.deleted_at.is_(None)).limit(1))
    assert token
    response = api.get(f"/api/v1/public/certificates/{token}")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["validation_hash"]) == 64
    forbidden = {"nif", "phone", "email", "user", "audit", "ip_address"}
    assert forbidden.isdisjoint(payload.keys())
    api.close()
