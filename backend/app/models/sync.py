from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class EnterpriseSyncEvent(RecordMixin, Base):
    __tablename__ = "enterprise_sync_events"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("device_registrations.id"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), default="push", index=True)
    provider: Mapped[str] = mapped_column(String(60), default="local-sqlite")
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    operation: Mapped[str] = mapped_column(String(30), default="upsert")
    payload_json: Mapped[str] = mapped_column(Text)
    cursor: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="accepted", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
