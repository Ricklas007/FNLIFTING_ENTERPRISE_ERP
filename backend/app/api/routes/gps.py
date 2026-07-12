from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import GPSIngestRequest
from app.services.gps_service import ingest_gps_event

router = APIRouter(prefix="/gps")


@router.post("/ingest", status_code=201)
def ingest_gps(payload: GPSIngestRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    event = ingest_gps_event(db, user, payload)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "status": event.status, "provider": event.provider}
