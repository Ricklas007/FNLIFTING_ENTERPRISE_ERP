from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class GPSIntegrationEvent(RecordMixin, Base):
    __tablename__ = "gps_integration_events"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(60), default="local-gps")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="processed", index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
