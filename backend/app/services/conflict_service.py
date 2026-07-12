from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SyncQueue, User
from app.sync.service import resolve_conflict


def list_conflicts(db: Session, user: User) -> list[SyncQueue]:
    return list(db.scalars(select(SyncQueue).where(SyncQueue.company_id == user.company_id, SyncQueue.status == "conflict", SyncQueue.deleted_at.is_(None)).order_by(SyncQueue.queued_at.desc())))


def resolve_queue_conflict(db: Session, user: User, entry_id: str, strategy: str, merged_payload: dict | None) -> SyncQueue | None:
    entry = db.scalar(select(SyncQueue).where(SyncQueue.id == entry_id, SyncQueue.company_id == user.company_id, SyncQueue.status == "conflict", SyncQueue.deleted_at.is_(None)))
    if not entry:
        return None
    resolve_conflict(db, entry, strategy, merged_payload, user.id)
    return entry
