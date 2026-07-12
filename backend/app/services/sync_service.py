from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DeviceRegistration, EnterpriseSyncEvent, SyncQueue, SyncRun, User
from app.services.enterprise_utils import from_json, now_utc, sync_provider_hint, to_json


def push_events(db: Session, user: User, device_uid: str | None, events: list[Any]) -> dict:
    device = None
    if device_uid:
        device = db.scalar(select(DeviceRegistration).where(DeviceRegistration.company_id == user.company_id, DeviceRegistration.device_uid == device_uid, DeviceRegistration.deleted_at.is_(None)))
    accepted = 0
    duplicates = 0
    for event in events:
        payload = event.payload if hasattr(event, "payload") else event.get("payload", {})
        cursor = event.cursor if hasattr(event, "cursor") else event.get("cursor")
        entity_type = event.entity_type if hasattr(event, "entity_type") else event["entity_type"]
        entity_id = event.entity_id if hasattr(event, "entity_id") else event["entity_id"]
        operation = event.operation if hasattr(event, "operation") else event.get("operation", "upsert")
        existing = db.scalar(select(EnterpriseSyncEvent.id).where(
            EnterpriseSyncEvent.company_id == user.company_id,
            EnterpriseSyncEvent.device_id == (device.id if device else None),
            EnterpriseSyncEvent.entity_type == entity_type,
            EnterpriseSyncEvent.entity_id == entity_id,
            EnterpriseSyncEvent.operation == operation,
            EnterpriseSyncEvent.cursor == cursor,
            EnterpriseSyncEvent.deleted_at.is_(None),
        ))
        if existing and cursor:
            duplicates += 1
            continue
        db.add(EnterpriseSyncEvent(
            company_id=user.company_id,
            device_id=device.id if device else None,
            direction="push",
            provider=sync_provider_hint(),
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload_json=to_json(payload),
            cursor=cursor,
            status="accepted",
            processed_at=now_utc(),
            created_by=user.id,
        ))
        accepted += 1
    return {"accepted": accepted, "duplicates": duplicates, "provider": sync_provider_hint(), "cursor": f"local-{int(now_utc().timestamp())}"}


def pull_events(db: Session, user: User, cursor: str | None, limit: int) -> dict:
    query = select(EnterpriseSyncEvent).where(EnterpriseSyncEvent.company_id == user.company_id, EnterpriseSyncEvent.deleted_at.is_(None))
    if cursor:
        query = query.where(EnterpriseSyncEvent.cursor > cursor)
    rows = list(db.scalars(query.order_by(EnterpriseSyncEvent.created_at.asc()).limit(limit)))
    return {
        "events": [{
            "id": item.id,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "operation": item.operation,
            "payload": from_json(item.payload_json, {}),
            "cursor": item.cursor,
            "status": item.status,
            "created_at": item.created_at,
        } for item in rows],
        "next_cursor": rows[-1].cursor if rows else cursor,
        "provider": sync_provider_hint(),
    }


def sync_status(db: Session, user: User) -> dict:
    return {
        "provider": sync_provider_hint(),
        "remote_configured": bool(settings.sync_remote_url),
        "events": db.scalar(select(func.count(EnterpriseSyncEvent.id)).where(EnterpriseSyncEvent.company_id == user.company_id, EnterpriseSyncEvent.deleted_at.is_(None))) or 0,
        "queue_pending": db.scalar(select(func.count(SyncQueue.id)).where(SyncQueue.company_id == user.company_id, SyncQueue.status == "pending", SyncQueue.deleted_at.is_(None))) or 0,
        "last_sync": db.scalar(select(func.max(SyncRun.completed_at)).where(SyncRun.company_id == user.company_id)),
    }
