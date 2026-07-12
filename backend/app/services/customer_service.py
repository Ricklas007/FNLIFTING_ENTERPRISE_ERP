from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustomerMessage, User


def list_customer_messages(db: Session, user: User) -> list[dict]:
    rows = db.scalars(select(CustomerMessage).where(CustomerMessage.company_id == user.company_id, CustomerMessage.deleted_at.is_(None)).order_by(CustomerMessage.created_at.desc()).limit(100))
    return [{
        "id": item.id,
        "client_id": item.client_id,
        "direction": item.direction,
        "channel": item.channel,
        "subject": item.subject,
        "body": item.body,
        "status": item.status,
        "created_at": item.created_at,
    } for item in rows]


def create_customer_message(db: Session, user: User, payload) -> CustomerMessage:
    record = CustomerMessage(
        company_id=user.company_id,
        client_id=payload.client_id,
        user_id=user.id,
        direction="inbound" if user.account_type == "external" else "outbound",
        channel=payload.channel,
        subject=payload.subject,
        body=payload.body,
        status="open",
        created_by=user.id,
    )
    db.add(record)
    return record
