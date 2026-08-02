from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin, utcnow


class MapPackage(RecordMixin, Base):
    __tablename__ = "map_packages"
    __table_args__ = (UniqueConstraint("company_id", "checksum_sha256", name="uq_map_package_company_checksum"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    original_name: Mapped[str] = mapped_column(String(260))
    stored_name: Mapped[str] = mapped_column(String(260), index=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    license: Mapped[str] = mapped_column(String(120), default="unknown")
    version: Mapped[str] = mapped_column(String(80), default="unknown")
    min_zoom: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_zoom: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bounds_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="manual")
    status: Mapped[str] = mapped_column(String(30), default="imported", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MapPackageValidation(RecordMixin, Base):
    __tablename__ = "map_package_validations"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("map_packages.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    checks_json: Mapped[str] = mapped_column(Text)
    errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MapPackageActivation(RecordMixin, Base):
    __tablename__ = "map_package_activations"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("map_packages.id"), index=True)
    previous_package_id: Mapped[str | None] = mapped_column(ForeignKey("map_packages.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MapPackageUsage(RecordMixin, Base):
    __tablename__ = "map_package_usage"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("map_packages.id"), index=True)
    usage_type: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bytes_served: Mapped[int] = mapped_column(Integer, default=0)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
