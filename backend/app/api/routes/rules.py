from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import AutomationRule, User
from app.schemas.enterprise import AutomationRuleCreate
from app.services.rule_engine import automation_center, create_rule

router = APIRouter(prefix="/ai/automation")


@router.get("")
def get_automation_center(user: User = Depends(require_permission("reports.view")), db: Session = Depends(get_db)):
    data = automation_center(db, user)
    db.commit()
    return data


@router.post("/rules", status_code=201)
def create_automation_rule(payload: AutomationRuleCreate, user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    exists = db.scalar(select(AutomationRule).where(AutomationRule.company_id == user.company_id, AutomationRule.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="Já existe uma regra com este código")
    record = create_rule(db, user, payload)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "code": record.code, "status": record.status}
