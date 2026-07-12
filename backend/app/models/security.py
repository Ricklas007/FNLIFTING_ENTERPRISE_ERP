from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin, utcnow


class DeviceRegistration(RecordMixin, Base):
    __tablename__ = "device_registrations"
    __table_args__ = (UniqueConstraint("company_id", "device_uid", name="uq_device_company_uid"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_uid: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str] = mapped_column(String(60), default="web")
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(30), default="managed")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class UserMFAFactor(RecordMixin, Base):
    __tablename__ = "user_mfa_factors"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    factor_type: Mapped[str] = mapped_column(String(30), default="totp")
    label: Mapped[str] = mapped_column(String(120), default="Aplicação autenticadora")
    secret: Mapped[str] = mapped_column(String(120))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)


class MFAChallenge(RecordMixin, Base):
    __tablename__ = "mfa_challenges"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_token: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)


class MFARecoveryCode(RecordMixin, Base):
    __tablename__ = "mfa_recovery_codes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(300))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)


class SecurityEvent(RecordMixin, Base):
    __tablename__ = "security_events"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", index=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
