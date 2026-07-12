from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationRule, AutomationRun, OCRJob, User
from app.services.enterprise_utils import from_json, to_json
from app.services.tenant_service import ensure_enterprise_seed


def automation_center(db: Session, user: User) -> dict:
    ensure_enterprise_seed(db, user)
    rules = db.scalars(select(AutomationRule).where(AutomationRule.company_id == user.company_id, AutomationRule.deleted_at.is_(None)).order_by(AutomationRule.module, AutomationRule.code))
    jobs = db.scalars(select(OCRJob).where(OCRJob.company_id == user.company_id, OCRJob.deleted_at.is_(None)).order_by(OCRJob.created_at.desc()).limit(20))
    runs = db.scalars(select(AutomationRun).where(AutomationRun.company_id == user.company_id, AutomationRun.deleted_at.is_(None)).order_by(AutomationRun.executed_at.desc()).limit(20))
    return {
        "rules": [{
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "module": item.module,
            "trigger_event": item.trigger_event,
            "condition": from_json(item.condition_json, {}),
            "action": from_json(item.action_json, {}),
            "severity": item.severity,
            "status": item.status,
        } for item in rules],
        "ocr_jobs": [{
            "id": item.id,
            "source_filename": item.source_filename,
            "provider": item.provider,
            "status": item.status,
            "confidence": item.confidence,
            "created_at": item.created_at,
        } for item in jobs],
        "runs": [{
            "id": item.id,
            "rule_id": item.rule_id,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "result": item.result,
            "detail": from_json(item.detail_json, {}),
            "executed_at": item.executed_at,
        } for item in runs],
    }


def create_rule(db: Session, user: User, payload) -> AutomationRule:
    record = AutomationRule(
        company_id=user.company_id,
        code=payload.code,
        name=payload.name,
        module=payload.module,
        trigger_event=payload.trigger_event,
        condition_json=to_json(payload.condition),
        action_json=to_json(payload.action),
        severity=payload.severity,
        status="active",
        created_by=user.id,
    )
    db.add(record)
    return record
