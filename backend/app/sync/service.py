from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import Base
from app.models import SyncQueue, SyncRun


def sync_summary(db: Session, company_id: str) -> dict:
    counts = dict(db.execute(
        select(SyncQueue.status, func.count(SyncQueue.id))
        .where(SyncQueue.company_id == company_id, SyncQueue.deleted_at.is_(None))
        .group_by(SyncQueue.status)
    ).all())
    last = db.scalar(
        select(SyncRun)
        .where(SyncRun.company_id == company_id, SyncRun.deleted_at.is_(None))
        .order_by(SyncRun.started_at.desc())
    )
    return {
        "connection": "ready" if settings.sync_remote_url else "local",
        "mode": "remote" if settings.sync_remote_url else "local_checkpoint",
        "remote_configured": bool(settings.sync_remote_url),
        "pending": counts.get("pending", 0),
        "synced": counts.get("synced", 0),
        "conflicts": counts.get("conflict", 0),
        "failed": counts.get("failed", 0),
        "last_sync_at": last.completed_at if last else None,
        "last_sync_status": last.status if last else None,
        "database": "SQLite local",
    }


def run_sync(db: Session, company_id: str, user_id: str, limit: int) -> SyncRun:
    mode = "remote" if settings.sync_remote_url else "local_checkpoint"
    run = SyncRun(
        company_id=company_id,
        direction="bidirectional",
        mode=mode,
        started_at=datetime.now(timezone.utc),
        status="running",
        created_by=user_id,
    )
    db.add(run)
    db.flush()

    entries = list(db.scalars(
        select(SyncQueue)
        .where(
            SyncQueue.company_id == company_id,
            SyncQueue.status.in_(["pending", "failed"]),
            SyncQueue.deleted_at.is_(None),
        )
        .order_by(SyncQueue.queued_at)
        .limit(limit)
    ))
    processed = 0
    failed = 0
    now = datetime.now(timezone.utc)
    for entry in entries:
        try:
            entry.status = "synced"
            entry.processed_at = now
            entry.error_message = None
            entry.updated_by = user_id
            table = Base.metadata.tables.get(entry.entity_type)
            if table is not None and "sync_status" in table.c and "id" in table.c:
                db.execute(table.update().where(table.c.id == entry.entity_id).values(sync_status="synced"))
            processed += 1
        except Exception as exc:  # pragma: no cover - proteção por entidade dinâmica
            entry.status = "failed"
            entry.retry_count += 1
            entry.error_message = str(exc)[:1000]
            failed += 1

    run.completed_at = now
    run.pushed_count = processed
    run.failed_count = failed
    run.conflict_count = db.scalar(select(func.count(SyncQueue.id)).where(
        SyncQueue.company_id == company_id, SyncQueue.status == "conflict"
    )) or 0
    run.status = "completed" if failed == 0 else "partial"
    run.message = (
        f"{processed} alterações consolidadas no checkpoint local. Configure SYNC_REMOTE_URL para o transporte cloud."
        if not settings.sync_remote_url
        else f"{processed} alterações preparadas para o endpoint remoto configurado."
    )
    return run


def resolve_conflict(db: Session, entry: SyncQueue, strategy: str, merged_payload: dict | None, user_id: str) -> SyncQueue:
    if strategy == "remote":
        entry.status = "synced"
        entry.processed_at = datetime.now(timezone.utc)
    else:
        if strategy == "merge" and merged_payload is not None:
            import json
            entry.payload = json.dumps(merged_payload, ensure_ascii=False, default=str)
        entry.status = "pending"
        entry.processed_at = None
    entry.error_message = None
    entry.updated_by = user_id
    return entry
