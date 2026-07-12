from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class ComplianceRequirement(RecordMixin, Base):
    __tablename__ = "compliance_requirements"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_compliance_company_code"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(220))
    category: Mapped[str] = mapped_column(String(80), index=True)
    authority: Mapped[str | None] = mapped_column(String(160), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    evidence_document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
