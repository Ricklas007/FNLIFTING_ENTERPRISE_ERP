from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import OCRJobCreate
from app.services.ocr_service import create_ocr_job

router = APIRouter(prefix="/ai/ocr")


@router.post("/jobs", status_code=201)
def create_job(payload: OCRJobCreate, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    record = create_ocr_job(db, user, payload)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status, "confidence": record.confidence, "extracted_text": record.extracted_text}
