from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import RecordMixin, utcnow


class GPSTrackerDevice(RecordMixin, Base):
    __tablename__ = "gps_tracker_devices"
    __table_args__ = (UniqueConstraint("company_id", "device_uid", name="uq_gps_device_company_uid"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"), nullable=True, index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)
    device_uid: Mapped[str] = mapped_column(String(120), index=True)
    label: Mapped[str] = mapped_column(String(160))
    provider: Mapped[str] = mapped_column(String(60), default="fnlifting-gps")
    token_hash: Mapped[str] = mapped_column(String(300))
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Geofence(RecordMixin, Base):
    __tablename__ = "geofences"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    geofence_type: Mapped[str] = mapped_column(String(40), default="BASE", index=True)
    shape_type: Mapped[str] = mapped_column(String(30), default="circle", index=True)
    geometry_json: Mapped[str] = mapped_column(Text)
    radius_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    alert_on_enter: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_exit: Mapped[bool] = mapped_column(Boolean, default=True)
    dwell_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class GeofenceEvent(RecordMixin, Base):
    __tablename__ = "geofence_events"
    __table_args__ = (UniqueConstraint("company_id", "dedupe_key", name="uq_geofence_event_dedupe"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    geofence_id: Mapped[str] = mapped_column(ForeignKey("geofences.id"), index=True)
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), index=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class FleetAlertRule(RecordMixin, Base):
    __tablename__ = "fleet_alert_rules"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_fleet_alert_rule_company_code"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180))
    alert_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning", index=True)
    condition_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)


class FleetAlert(RecordMixin, Base):
    __tablename__ = "fleet_alerts"
    __table_args__ = (UniqueConstraint("company_id", "dedupe_key", name="uq_fleet_alert_dedupe"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("fleet_alert_rules.id"), nullable=True, index=True)
    geofence_event_id: Mapped[str | None] = mapped_column(ForeignKey("geofence_events.id"), nullable=True, index=True)
    truck_id: Mapped[str | None] = mapped_column(ForeignKey("trucks.id"), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning", index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(180), index=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
