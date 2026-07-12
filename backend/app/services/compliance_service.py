from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplianceRequirement, User
from app.services.tenant_service import ensure_enterprise_seed


def list_compliance(db: Session, user: User) -> list[dict]:
    ensure_enterprise_seed(db, user)
    rows = db.scalars(select(ComplianceRequirement).where(ComplianceRequirement.company_id == user.company_id, ComplianceRequirement.deleted_at.is_(None)).order_by(ComplianceRequirement.due_date.asc()))
    return [{
        "id": item.id,
        "code": item.code,
        "title": item.title,
        "category": item.category,
        "authority": item.authority,
        "due_date": item.due_date,
        "risk_level": item.risk_level,
        "status": item.status,
    } for item in rows]


def create_compliance(db: Session, user: User, payload) -> ComplianceRequirement:
    record = ComplianceRequirement(
        company_id=user.company_id,
        code=payload.code,
        title=payload.title,
        category=payload.category,
        authority=payload.authority,
        due_date=payload.due_date,
        risk_level=payload.risk_level,
        status="open",
        created_by=user.id,
    )
    db.add(record)
    return record
