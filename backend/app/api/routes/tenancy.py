from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.services.tenant_service import enterprise_overview

router = APIRouter()


@router.get("/overview")
def overview(user: User = Depends(require_permission("dashboard.view")), db: Session = Depends(get_db)):
    data = enterprise_overview(db, user)
    db.commit()
    return data
