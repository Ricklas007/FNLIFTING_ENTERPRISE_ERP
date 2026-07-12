from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import RecordMixin, utcnow


class AIProviderSetting(RecordMixin, Base):
    __tablename__ = "ai_provider_settings"
    __table_args__ = (UniqueConstraint("company_id", "provider_type", "provider_name", name="uq_ai_provider_company_type_name"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    provider_type: Mapped[str] = mapped_column(String(40), index=True)
    provider_name: Mapped[str] = mapped_column(String(80), default="local")
    mode: Mapped[str] = mapped_column(String(30), default="local")
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_hint: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)


class OCRJob(RecordMixin, Base):
    __tablename__ = "ocr_jobs"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    certificate_id: Mapped[str | None] = mapped_column(ForeignKey("certificates.id"), nullable=True, index=True)
    source_filename: Mapped[str] = mapped_column(String(240))
    source_mime: Mapped[str] = mapped_column(String(100), default="application/pdf")
    provider: Mapped[str] = mapped_column(String(80), default="local")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutomationRule(RecordMixin, Base):
    __tablename__ = "automation_rules"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_automation_rule_company_code"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    module: Mapped[str] = mapped_column(String(60), index=True)
    trigger_event: Mapped[str] = mapped_column(String(120))
    condition_json: Mapped[str] = mapped_column(Text)
    action_json: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)

    runs: Mapped[list["AutomationRun"]] = relationship(back_populates="rule", cascade="all, delete-orphan")


class AutomationRun(RecordMixin, Base):
    __tablename__ = "automation_runs"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey("automation_rules.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    result: Mapped[str] = mapped_column(String(30), default="executed", index=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    rule: Mapped[AutomationRule] = relationship(back_populates="runs")
