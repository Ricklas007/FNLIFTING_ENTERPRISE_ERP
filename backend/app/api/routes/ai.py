from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.services.ai_service import list_ai_providers

router = APIRouter(prefix="/ai")


@router.get("/providers")
def ai_providers(user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    result = list_ai_providers(db, user)
    db.commit()
    return result
