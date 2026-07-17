from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models import AIAssistantSuggestion, AIProviderSetting, AutomationRule, OCRJob, User
from app.services.enterprise_utils import from_json, to_json
from app.services.notification_service import create_notification
from app.services.tenant_service import ensure_enterprise_seed


def list_ai_providers(db: Session, user: User) -> list[dict]:
    ensure_enterprise_seed(db, user)
    rows = db.scalars(select(AIProviderSetting).where(AIProviderSetting.company_id == user.company_id, AIProviderSetting.deleted_at.is_(None)).order_by(AIProviderSetting.provider_type))
    return [{
        "id": item.id,
        "provider_type": item.provider_type,
        "provider_name": item.provider_name,
        "mode": item.mode,
        "endpoint_url": item.endpoint_url,
        "status": item.status,
    } for item in rows]


def _suggestion_payload(item: AIAssistantSuggestion) -> dict:
    return {
        "id": item.id,
        "module": item.module,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "title": item.title,
        "recommendation": item.recommendation,
        "rationale": item.rationale,
        "action": from_json(item.action_json, {}),
        "status": item.status,
        "reviewed_by": item.reviewed_by,
        "reviewed_at": item.reviewed_at,
        "applied_at": item.applied_at,
        "created_at": item.created_at,
    }


def _ensure_suggestion(db: Session, user: User, *, module: str, source_type: str, source_id: str, title: str, recommendation: str, rationale: str, action: dict) -> AIAssistantSuggestion:
    existing = db.scalar(select(AIAssistantSuggestion).where(
        AIAssistantSuggestion.company_id == user.company_id,
        AIAssistantSuggestion.source_type == source_type,
        AIAssistantSuggestion.source_id == source_id,
        AIAssistantSuggestion.title == title,
        AIAssistantSuggestion.deleted_at.is_(None),
    ))
    if existing:
        return existing
    record = AIAssistantSuggestion(
        company_id=user.company_id,
        module=module,
        source_type=source_type,
        source_id=source_id,
        title=title,
        recommendation=recommendation,
        rationale=rationale,
        action_json=to_json(action),
        status="pending",
        created_by=user.id,
    )
    db.add(record)
    return record


def generate_ai_assistant_suggestions(db: Session, user: User, module: str | None = None) -> list[dict]:
    ensure_enterprise_seed(db, user)
    created: list[AIAssistantSuggestion] = []
    ocr_query = select(OCRJob).where(OCRJob.company_id == user.company_id, OCRJob.deleted_at.is_(None), OCRJob.status.in_(["queued", "review_required"]))
    if module and module != "ocr":
        ocr_query = ocr_query.where(False)
    for job in db.scalars(ocr_query.order_by(OCRJob.created_at.desc()).limit(40)):
        created.append(_ensure_suggestion(
            db,
            user,
            module="ocr",
            source_type="ocr_job",
            source_id=job.id,
            title=f"Rever OCR: {job.source_filename}",
            recommendation="Validar campos extraídos, corrigir discrepâncias e só depois aprovar o documento associado.",
            rationale=f"O job OCR está em estado {job.status} com confiança {round((job.confidence or 0) * 100)}%, exigindo revisão humana antes de alimentar workflows.",
            action={"type": "open_ocr_review", "ocr_job_id": job.id, "document_id": job.document_id, "certificate_id": job.certificate_id},
        ))
    rule_query = select(AutomationRule).where(AutomationRule.company_id == user.company_id, AutomationRule.deleted_at.is_(None), AutomationRule.status == "active")
    if module and module != "rules":
        rule_query = rule_query.where(False)
    for rule in db.scalars(rule_query.order_by(AutomationRule.severity.desc(), AutomationRule.code).limit(40)):
        created.append(_ensure_suggestion(
            db,
            user,
            module="rules",
            source_type="automation_rule",
            source_id=rule.id,
            title=f"Monitorizar regra: {rule.code}",
            recommendation=f"Acompanhar a regra {rule.name} e executar a ação configurada quando o evento {rule.trigger_event} ocorrer.",
            rationale=f"Regra ativa de severidade {rule.severity}; condição e ação estão persistidas no rule engine.",
            action={"type": "monitor_rule", "rule_id": rule.id, "condition": from_json(rule.condition_json, {}), "action": from_json(rule.action_json, {})},
        ))
    db.flush()
    return [_suggestion_payload(item) for item in created]


def ai_assistant_center(db: Session, user: User) -> dict:
    generate_ai_assistant_suggestions(db, user)
    rows = list(db.scalars(select(AIAssistantSuggestion).where(
        AIAssistantSuggestion.company_id == user.company_id,
        AIAssistantSuggestion.deleted_at.is_(None),
    ).order_by(AIAssistantSuggestion.created_at.desc()).limit(120)))
    summary = {
        "pending": sum(1 for item in rows if item.status == "pending"),
        "accepted": sum(1 for item in rows if item.status == "accepted"),
        "edited": sum(1 for item in rows if item.status == "edited"),
        "rejected": sum(1 for item in rows if item.status == "rejected"),
    }
    return {"summary": summary, "suggestions": [_suggestion_payload(item) for item in rows]}


def review_ai_assistant_suggestion(db: Session, user: User, suggestion_id: str, payload) -> AIAssistantSuggestion:
    record = db.scalar(select(AIAssistantSuggestion).where(
        AIAssistantSuggestion.id == suggestion_id,
        AIAssistantSuggestion.company_id == user.company_id,
        AIAssistantSuggestion.deleted_at.is_(None),
    ))
    if not record:
        raise ValueError("Sugestão IA não encontrada")
    if payload.recommendation:
        record.recommendation = payload.recommendation
    if payload.rationale is not None:
        record.rationale = payload.rationale
    if payload.action is not None:
        record.action_json = to_json(payload.action)
    record.status = payload.status
    record.reviewed_by = user.id
    now = utcnow()
    record.reviewed_at = now
    record.applied_at = now if payload.status == "accepted" else None
    create_notification(
        db,
        user.company_id,
        "Sugestão IA revista",
        f"{record.title} · {payload.status}",
        "success" if payload.status in {"accepted", "edited"} else "info",
        created_by=user.id,
    )
    return record
