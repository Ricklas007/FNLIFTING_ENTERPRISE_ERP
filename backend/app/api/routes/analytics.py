from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.services.analytics_service import executive_bi

router = APIRouter(prefix="/bi")


@router.get("/executive")
def executive(user: User = Depends(require_permission("reports.view")), db: Session = Depends(get_db)):
    return executive_bi(db, user)
