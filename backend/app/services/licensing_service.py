from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, SaaSLicense, User
from app.services.enterprise_utils import from_json, to_json
from app.services.tenant_service import ensure_enterprise_seed


def license_status(db: Session, user: User) -> dict:
    ensure_enterprise_seed(db, user)
    company = db.get(Company, user.company_id)
    record = db.scalar(select(SaaSLicense).where(SaaSLicense.company_id == user.company_id, SaaSLicense.deleted_at.is_(None)).order_by(SaaSLicense.created_at.desc()))
    return {
        "company": {"id": company.id, "name": company.name, "type": company.company_type} if company else None,
        "license": {
            "id": record.id,
            "plan_code": record.plan_code,
            "seats": record.seats,
            "modules": from_json(record.modules_json, []),
            "starts_at": record.starts_at,
            "expires_at": record.expires_at,
            "status": record.status,
            "usage": from_json(record.usage_json, {}),
        } if record else None,
    }


def update_license(db: Session, user: User, payload) -> SaaSLicense:
    record = db.scalar(select(SaaSLicense).where(SaaSLicense.company_id == user.company_id, SaaSLicense.deleted_at.is_(None)).order_by(SaaSLicense.created_at.desc()))
    if not record:
        record = SaaSLicense(company_id=user.company_id, starts_at=payload.starts_at or date.today(), modules_json="[]", created_by=user.id)
        db.add(record)
    record.plan_code = payload.plan_code
    record.seats = payload.seats
    record.modules_json = to_json(payload.modules)
    record.starts_at = payload.starts_at or record.starts_at or date.today()
    record.expires_at = payload.expires_at
    record.status = "active"
    record.updated_by = user.id
    return record
