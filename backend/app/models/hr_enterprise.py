from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class AttendanceRecord(RecordMixin, Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("company_id", "employee_id", "work_date", name="uq_attendance_employee_date"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="present", index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)


class LeaveRequest(RecordMixin, Base):
    __tablename__ = "leave_requests"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(50), default="annual")
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
