from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin


class SaaSLicense(RecordMixin, Base):
    __tablename__ = "saas_licenses"
    __table_args__ = (UniqueConstraint("company_id", "plan_code", name="uq_saas_company_plan"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    plan_code: Mapped[str] = mapped_column(String(60), default="enterprise")
    seats: Mapped[int] = mapped_column(Integer, default=25)
    modules_json: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[date] = mapped_column(Date)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
