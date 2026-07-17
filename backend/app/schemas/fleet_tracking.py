from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GPSTrackerDeviceCreate(BaseModel):
    device_uid: str = Field(min_length=4, max_length=120)
    label: str = Field(min_length=2, max_length=160)
    truck_id: str | None = None
    driver_id: str | None = None
    provider: str = Field(default="fnlifting-gps", max_length=60)
    capabilities: list[str] = Field(default_factory=lambda: ["gps", "speed", "fuel"])
    status: str = Field(default="active", pattern="^(active|inactive|revoked)$")


class GPSTrackerDeviceOut(BaseModel):
    id: str
    device_uid: str
    label: str
    truck_id: str | None
    driver_id: str | None
    provider: str
    capabilities: list[str]
    status: str
    last_seen_at: datetime | None
    created_at: datetime


class GPSTrackerDeviceWithToken(GPSTrackerDeviceOut):
    token: str


class GPSDeviceIngestRequest(BaseModel):
    event_id: str = Field(min_length=3, max_length=160)
    truck_id: str | None = None
    driver_id: str | None = None
    trip_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kmh: float = Field(default=0, ge=0, le=260)
    heading: float | None = Field(default=None, ge=0, le=360)
    accuracy_meters: float | None = Field(default=None, ge=0, le=5000)
    ignition_status: str | None = Field(default=None, max_length=40)
    fuel_level_percent: float | None = Field(default=None, ge=0, le=100)
    odometer_km: float | None = Field(default=None, ge=0)
    vehicle_state: str = Field(default="moving", pattern="^(moving|stopped|offline|incident)$")
    timestamp: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class GeofenceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    geofence_type: str = Field(default="BASE", pattern="^(BASE|CLIENT|DEPOT|FUEL_STATION|TERMINAL|PORT|RESTRICTED|CHECKPOINT|PROVINCE|MUNICIPALITY)$")
    shape_type: str = Field(default="circle", pattern="^(circle|polygon|corridor|point)$")
    geometry: dict[str, Any]
    radius_meters: float | None = Field(default=None, gt=0)
    alert_on_enter: bool = True
    alert_on_exit: bool = True
    dwell_minutes: int | None = Field(default=None, ge=1, le=10080)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class GeofenceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    geofence_type: str | None = Field(default=None, pattern="^(BASE|CLIENT|DEPOT|FUEL_STATION|TERMINAL|PORT|RESTRICTED|CHECKPOINT|PROVINCE|MUNICIPALITY)$")
    shape_type: str | None = Field(default=None, pattern="^(circle|polygon|corridor|point)$")
    geometry: dict[str, Any] | None = None
    radius_meters: float | None = Field(default=None, gt=0)
    alert_on_enter: bool | None = None
    alert_on_exit: bool | None = None
    dwell_minutes: int | None = Field(default=None, ge=1, le=10080)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class GeofenceOut(BaseModel):
    id: str
    name: str
    geofence_type: str
    shape_type: str
    geometry: dict[str, Any]
    radius_meters: float | None
    alert_on_enter: bool
    alert_on_exit: bool
    dwell_minutes: int | None
    status: str
    created_at: datetime


class FleetAlertRuleCreate(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    alert_type: str = Field(min_length=3, max_length=60)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    condition: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class FleetAlertOut(BaseModel):
    id: str
    truck_id: str | None
    trip_id: str | None
    alert_type: str
    severity: str
    title: str
    message: str
    status: str
    triggered_at: datetime
    resolved_at: datetime | None
    payload: dict[str, Any]


class FleetAlertRuleOut(BaseModel):
    id: str
    code: str
    name: str
    alert_type: str
    severity: str
    condition: dict[str, Any]
    status: str
    created_at: datetime


class GPSReplayOut(BaseModel):
    mode: str
    count: int
    bounds: list[float] | None
    positions: list[dict[str, Any]]
    stops: list[dict[str, Any]]


class DeviceIngestOut(BaseModel):
    event_id: str
    integration_event_id: str
    gps_position_id: str | None
    status: str
    alerts_created: int
    geofence_events_created: int

    model_config = ConfigDict(from_attributes=True)
