from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import ComplianceRequirement, User
from app.schemas.enterprise import ComplianceCreate
from app.services.compliance_service import create_compliance, list_compliance

router = APIRouter(prefix="/compliance")


@router.get("")
def compliance_center(user: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    data = list_compliance(db, user)
    db.commit()
    return data


@router.post("", status_code=201)
def post_compliance(payload: ComplianceCreate, user: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    exists = db.scalar(select(ComplianceRequirement).where(ComplianceRequirement.company_id == user.company_id, ComplianceRequirement.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="Já existe requisito com este código")
    record = create_compliance(db, user, payload)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "code": record.code, "status": record.status}
