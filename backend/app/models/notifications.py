from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class NotificationDelivery(RecordMixin, Base):
    __tablename__ = "notification_deliveries"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(30), default="in_app")
    provider: Mapped[str] = mapped_column(String(60), default="local")
    destination: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
