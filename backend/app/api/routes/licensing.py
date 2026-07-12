from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import LicenseUpdate
from app.services.licensing_service import license_status, update_license

router = APIRouter(prefix="/saas")


@router.get("/license")
def get_license_status(user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    data = license_status(db, user)
    db.commit()
    return data


@router.patch("/license")
def patch_license(payload: LicenseUpdate, user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    record = update_license(db, user, payload)
    db.commit()
    return {"id": record.id, "plan_code": record.plan_code, "seats": record.seats}
