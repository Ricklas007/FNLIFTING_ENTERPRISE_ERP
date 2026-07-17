from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    device_uid: str = Field(min_length=6, max_length=120)
    name: str = Field(min_length=2, max_length=160)
    platform: str = Field(default="web", max_length=60)
    app_version: str | None = Field(default=None, max_length=40)
    capabilities: list[str] = Field(default_factory=list)
    public_key: str | None = None


class SyncEventIn(BaseModel):
    entity_type: str = Field(min_length=2, max_length=100)
    entity_id: str = Field(min_length=1, max_length=80)
    operation: str = Field(default="upsert", pattern="^(create|update|delete|upsert)$")
    payload: dict
    cursor: str | None = Field(default=None, max_length=120)


class SyncPushRequest(BaseModel):
    device_uid: str | None = Field(default=None, max_length=120)
    events: list[SyncEventIn] = Field(min_length=1, max_length=500)


class MFAConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class FleetCommandCreate(BaseModel):
    command_type: str = Field(min_length=2, max_length=60)
    truck_id: str | None = None
    trip_id: str | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    payload: dict = Field(default_factory=dict)
    assigned_to: str | None = None
    due_at: datetime | None = None


class GPSIngestRequest(BaseModel):
    provider: str = Field(default="local-gps", max_length=60)
    truck_id: str | None = None
    trip_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    speed_kmh: float | None = Field(default=None, ge=0)
    payload: dict = Field(default_factory=dict)


class OCRJobCreate(BaseModel):
    source_filename: str = Field(min_length=3, max_length=240)
    source_mime: str = Field(default="application/pdf", max_length=100)
    document_id: str | None = None
    certificate_id: str | None = None
    provider: str = Field(default="local", max_length=80)
    sample_text: str | None = None


class AutomationRuleCreate(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    module: str = Field(min_length=2, max_length=60)
    trigger_event: str = Field(min_length=3, max_length=120)
    condition: dict = Field(default_factory=dict)
    action: dict = Field(default_factory=dict)
    severity: str = Field(default="info", pattern="^(info|warning|critical)$")


class AIAssistantSuggestionReview(BaseModel):
    status: str = Field(pattern="^(pending|accepted|rejected|edited)$")
    recommendation: str | None = Field(default=None, min_length=3)
    rationale: str | None = None
    action: dict | None = None


class AttendanceCreate(BaseModel):
    employee_id: str
    work_date: date
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    location: str | None = Field(default=None, max_length=180)
    status: str = Field(default="present", pattern="^(present|late|absent|remote|leave)$")


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type: str = Field(default="annual", max_length=50)
    start_date: date
    end_date: date
    reason: str | None = None


class OrgPositionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=160)
    department_id: str
    employee_id: str | None = None
    supervisor_position_id: str | None = None
    level: int = Field(default=1, ge=0, le=30)


class PayrollRunCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")


class ComplianceCreate(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=3, max_length=220)
    category: str = Field(min_length=2, max_length=80)
    authority: str | None = Field(default=None, max_length=160)
    due_date: date | None = None
    risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class CustomerMessageCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=220)
    body: str = Field(min_length=3)
    client_id: str | None = None
    channel: str = Field(default="portal", max_length=40)


class LicenseUpdate(BaseModel):
    plan_code: str = Field(default="enterprise", max_length=60)
    seats: int = Field(default=25, ge=1, le=10000)
    modules: list[str] = Field(default_factory=list)
    starts_at: date | None = None
    expires_at: date | None = None


class PayrollLine(BaseModel):
    employee_id: str
    gross_pay: Decimal
    deductions: Decimal
