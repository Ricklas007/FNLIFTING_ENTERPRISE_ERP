from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class FleetCommand(RecordMixin, Base):
    __tablename__ = "fleet_commands"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    command_type: Mapped[str] = mapped_column(String(60), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
