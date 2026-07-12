from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Certificate, ComplianceRequirement, Employee, Invoice, User
from app.services.enterprise_utils import sync_provider_hint


def executive_bi(db: Session, user: User) -> dict:
    company_id = user.company_id
    revenue = db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.company_id == company_id, Invoice.deleted_at.is_(None))) or 0
    certificates = db.scalar(select(func.count(Certificate.id)).where(Certificate.company_id == company_id, Certificate.deleted_at.is_(None))) or 0
    employees = db.scalar(select(func.count(Employee.id)).where(Employee.company_id == company_id, Employee.deleted_at.is_(None))) or 0
    compliance_open = db.scalar(select(func.count(ComplianceRequirement.id)).where(ComplianceRequirement.company_id == company_id, ComplianceRequirement.status == "open", ComplianceRequirement.deleted_at.is_(None))) or 0
    return {
        "scorecards": [
            {"key": "revenue", "label": "Faturação total", "value": float(revenue), "display": f"{float(revenue):,.0f} AOA"},
            {"key": "certificates", "label": "Certificados rastreados", "value": certificates, "display": str(certificates)},
            {"key": "employees", "label": "Trabalhadores", "value": employees, "display": str(employees)},
            {"key": "compliance_open", "label": "Itens de compliance abertos", "value": compliance_open, "display": str(compliance_open)},
        ],
        "risk": {
            "level": "high" if compliance_open > 3 else "medium" if compliance_open else "low",
            "remote_sync": bool(settings.sync_remote_url),
            "provider": sync_provider_hint(),
        },
    }
