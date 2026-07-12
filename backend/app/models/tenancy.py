from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class CustomerMessage(RecordMixin, Base):
    __tablename__ = "customer_messages"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), default="inbound", index=True)
    channel: Mapped[str] = mapped_column(String(40), default="portal")
    subject: Mapped[str] = mapped_column(String(220))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
