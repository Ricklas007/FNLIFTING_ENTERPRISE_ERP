from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import SyncPushRequest
from app.schemas.system import ConflictResolve, SyncQueueOut
from app.services import conflict_service, sync_service

router = APIRouter(prefix="/sync")


@router.post("/push")
def sync_push(payload: SyncPushRequest, user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    result = sync_service.push_events(db, user, payload.device_uid, payload.events)
    db.commit()
    return result


@router.get("/pull")
def sync_pull(cursor: str | None = None, limit: int = Query(default=100, ge=1, le=500), user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return sync_service.pull_events(db, user, cursor, limit)


@router.get("/status")
def sync_status(user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return sync_service.sync_status(db, user)


@router.get("/conflicts", response_model=list[SyncQueueOut])
def list_conflicts(user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return conflict_service.list_conflicts(db, user)


@router.post("/conflicts/{entry_id}/resolve", response_model=SyncQueueOut)
def resolve_conflict(entry_id: str, payload: ConflictResolve, user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    entry = conflict_service.resolve_queue_conflict(db, user, entry_id, payload.strategy, payload.merged_payload)
    if not entry:
        raise HTTPException(status_code=404, detail="Conflito de sincronização não encontrado")
    db.commit()
    db.refresh(entry)
    return entry
