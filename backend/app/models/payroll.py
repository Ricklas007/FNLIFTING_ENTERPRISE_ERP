from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import RecordMixin


class PayrollRun(RecordMixin, Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("company_id", "period", name="uq_payroll_company_period"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    gross_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    deduction_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    net_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["PayrollItem"]] = relationship(back_populates="payroll_run", cascade="all, delete-orphan")


class PayrollItem(RecordMixin, Base):
    __tablename__ = "payroll_items"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    payroll_run_id: Mapped[str] = mapped_column(ForeignKey("payroll_runs.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    deductions: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)

    payroll_run: Mapped[PayrollRun] = relationship(back_populates="items")
