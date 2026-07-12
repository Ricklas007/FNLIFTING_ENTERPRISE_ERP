from sqlalchemy.orm import Session

from app.models import OCRJob, User
from app.services.enterprise_utils import to_json
from app.services.notification_service import create_notification


def create_ocr_job(db: Session, user: User, payload) -> OCRJob:
    extracted_text = payload.sample_text or f"Processamento OCR local preparado para {payload.source_filename}."
    confidence = 0.82 if payload.sample_text else 0.55
    record = OCRJob(
        company_id=user.company_id,
        document_id=payload.document_id,
        certificate_id=payload.certificate_id,
        source_filename=payload.source_filename,
        source_mime=payload.source_mime,
        provider=payload.provider,
        status="review_required",
        extracted_text=extracted_text,
        extracted_json=to_json({"fields": {"source": payload.source_filename, "mode": "local"}, "needs_review": True}),
        confidence=confidence,
        created_by=user.id,
    )
    db.add(record)
    create_notification(db, user.company_id, "OCR pronto para revisão", payload.source_filename, "info", created_by=user.id)
    return record
