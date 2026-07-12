import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.common import RecordMixin, utcnow, uuid4_str
from app.models.domain import SyncQueue


EXCLUDED_TABLES = {
    "audit_logs",
    "backups",
    "login_history",
    "sync_queue",
    "sync_runs",
    "user_sessions",
}


def _json_value(value):
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value


def _serialize(record) -> dict:
    state = inspect(record)
    return {
        attribute.key: _json_value(getattr(record, attribute.key, None))
        for attribute in state.mapper.column_attrs
    }


@event.listens_for(Session, "before_flush")
def queue_local_changes(session: Session, _flush_context, _instances) -> None:
    """Regista cada mutação local na mesma transação que altera o dado."""
    if session.info.get("skip_sync_queue"):
        return

    candidates = list(session.new) + list(session.dirty) + list(session.deleted)
    seen: set[int] = set()
    for record in candidates:
        if id(record) in seen or not isinstance(record, RecordMixin):
            continue
        seen.add(id(record))
        table_name = getattr(record, "__tablename__", "")
        if table_name in EXCLUDED_TABLES or not hasattr(record, "company_id"):
            continue
        if record in session.dirty and not session.is_modified(record, include_collections=False):
            continue

        company_id = getattr(record, "company_id", None)
        if not company_id:
            continue
        if not getattr(record, "id", None):
            record.id = uuid4_str()

        operation = "delete" if record in session.deleted else "create" if record in session.new else "update"
        payload = _serialize(record)
        if operation != "delete" and hasattr(record, "sync_status"):
            record.sync_status = "pending"
            payload["sync_status"] = "pending"

        session.add(SyncQueue(
            id=uuid4_str(),
            company_id=company_id,
            entity_type=table_name,
            entity_id=record.id,
            operation=operation,
            payload=json.dumps(payload, ensure_ascii=False, default=str),
            base_version=str(getattr(record, "updated_at", "") or "") or None,
            status="pending",
            queued_at=utcnow(),
            created_by=getattr(record, "updated_by", None) or getattr(record, "created_by", None),
        ))
