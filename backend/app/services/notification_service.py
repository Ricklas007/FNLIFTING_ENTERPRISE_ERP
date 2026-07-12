from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, NotificationDelivery, User
from app.services.enterprise_utils import now_utc, to_json


def create_notification(
    db: Session,
    company_id: str,
    title: str,
    message: str,
    level: str = "info",
    user_id: str | None = None,
    created_by: str | None = None,
    dedupe_key: str | None = None,
) -> Notification:
    if dedupe_key:
        existing = db.scalar(select(Notification).where(
            Notification.company_id == company_id,
            Notification.title == title,
            Notification.message == message,
            Notification.status == "unread",
            Notification.deleted_at.is_(None),
        ))
        if existing:
            return existing
    record = Notification(
        company_id=company_id,
        user_id=user_id,
        title=title,
        message=message,
        level=level,
        status="unread",
        created_by=created_by,
    )
    db.add(record)
    db.flush()
    db.add(NotificationDelivery(
        company_id=company_id,
        notification_id=record.id,
        channel="in_app",
        provider="local",
        destination=user_id,
        status="sent",
        sent_at=now_utc(),
        detail_json=to_json({"dedupe_key": dedupe_key} if dedupe_key else {}),
        created_by=created_by,
    ))
    return record


def list_notifications(db: Session, user: User, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.scalars(select(Notification).where(
        Notification.company_id == user.company_id,
        Notification.deleted_at.is_(None),
        (Notification.user_id.is_(None) | (Notification.user_id == user.id)),
    ).order_by(Notification.created_at.desc()).limit(limit))
    return [serialize_notification(item) for item in rows]


def mark_read(db: Session, user: User, notification_id: str) -> dict[str, Any] | None:
    item = db.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.company_id == user.company_id,
        Notification.deleted_at.is_(None),
    ))
    if not item or (item.user_id and item.user_id != user.id):
        return None
    item.status = "read"
    item.updated_by = user.id
    return serialize_notification(item)


def serialize_notification(item: Notification) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "message": item.message,
        "level": item.level,
        "status": item.status,
        "created_at": item.created_at,
        "user_id": item.user_id,
    }
