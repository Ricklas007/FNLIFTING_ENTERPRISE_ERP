from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import AIAssistantSuggestionReview
from app.services.ai_service import ai_assistant_center, generate_ai_assistant_suggestions, list_ai_providers, review_ai_assistant_suggestion

router = APIRouter(prefix="/ai")


@router.get("/providers")
def ai_providers(user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    result = list_ai_providers(db, user)
    db.commit()
    return result


@router.get("/assistant")
def assistant_center(user: User = Depends(require_permission("operations.view")), db: Session = Depends(get_db)):
    result = ai_assistant_center(db, user)
    db.commit()
    return result


@router.post("/assistant/generate")
def generate_assistant(module: str | None = None, user: User = Depends(require_permission("operations.view")), db: Session = Depends(get_db)):
    result = generate_ai_assistant_suggestions(db, user, module)
    db.commit()
    return {"count": len(result), "suggestions": result}


@router.patch("/assistant/{suggestion_id}")
def review_assistant_suggestion(suggestion_id: str, payload: AIAssistantSuggestionReview, user: User = Depends(require_permission("operations.manage")), db: Session = Depends(get_db)):
    try:
        record = review_ai_assistant_suggestion(db, user, suggestion_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "status": record.status,
        "recommendation": record.recommendation,
        "reviewed_at": record.reviewed_at,
        "applied_at": record.applied_at,
    }
