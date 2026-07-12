import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def from_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def sync_provider_hint() -> str:
    return "cloud" if settings.sync_remote_url else "local-sqlite"
