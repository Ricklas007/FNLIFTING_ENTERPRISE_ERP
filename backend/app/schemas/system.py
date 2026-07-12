from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.management import DocumentOut, InvoiceOut, ReceiptOut
from app.schemas.operations import ClientOut, EquipmentOut


class BackupCreate(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    include_files: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class BackupRestore(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    confirm: bool = False


class BackupOut(BaseModel):
    id: str
    backup_no: str
    file_name: str
    file_size: int
    checksum_sha256: str
    format_version: str
    encrypted: bool
    includes_files: bool
    status: str
    triggered_by: str
    restored_at: datetime | None
    notes: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SyncQueueOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    operation: str
    payload: str
    base_version: str | None
    status: str
    retry_count: int
    error_message: str | None
    conflict_payload: str | None
    queued_at: datetime
    processed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class SyncRunOut(BaseModel):
    id: str
    direction: str
    mode: str
    started_at: datetime
    completed_at: datetime | None
    pushed_count: int
    pulled_count: int
    conflict_count: int
    failed_count: int
    status: str
    message: str | None
    model_config = ConfigDict(from_attributes=True)


class SyncSummary(BaseModel):
    connection: str
    mode: str
    remote_configured: bool
    pending: int
    synced: int
    conflicts: int
    failed: int
    last_sync_at: datetime | None
    last_sync_status: str | None
    database: str


class SyncRunRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=1000)


class ConflictResolve(BaseModel):
    strategy: str = Field(pattern="^(local|remote|merge)$")
    merged_payload: dict | None = None


class SettingOut(BaseModel):
    id: str
    key: str
    label: str
    value: str
    value_type: str
    category: str
    is_secret: bool
    description: str | None
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str = Field(max_length=4000)


class ServiceRequestCreate(BaseModel):
    equipment_id: str | None = None
    service_type: str = Field(default="inspection", pattern="^(inspection|certification|maintenance|consulting)$")
    preferred_date: date | None = None
    location: str = Field(min_length=2, max_length=220)
    contact_name: str = Field(min_length=2, max_length=180)
    contact_phone: str | None = Field(default=None, max_length=40)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    notes: str | None = Field(default=None, max_length=3000)


class ServiceRequestUpdate(BaseModel):
    status: str = Field(pattern="^(submitted|reviewing|scheduled|completed|rejected|cancelled)$")
    response_notes: str | None = Field(default=None, max_length=3000)


class ServiceRequestOut(BaseModel):
    id: str
    request_no: str
    service_type: str
    requested_date: date
    preferred_date: date | None
    location: str
    contact_name: str
    contact_phone: str | None
    priority: str
    notes: str | None
    status: str
    response_notes: str | None
    handled_at: datetime | None
    client: ClientOut
    equipment: EquipmentOut | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PortalOverview(BaseModel):
    client_name: str
    equipment_total: int
    certificates_valid: int
    certificates_expiring: int
    invoices_open: int
    amount_due: float
    documents_available: int
    requests_open: int
    latest_requests: list[ServiceRequestOut]


class PortalBilling(BaseModel):
    invoices: list[InvoiceOut]
    receipts: list[ReceiptOut]


class PortalDocuments(BaseModel):
    documents: list[DocumentOut]


class ReportMetric(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    variation: float | None = None


class ReportSeriesPoint(BaseModel):
    period: str
    revenue: float
    expense: float
    inspections: int
    trips: int


class AdvancedReport(BaseModel):
    report_type: str
    title: str
    date_from: date
    date_to: date
    generated_at: datetime
    metrics: list[ReportMetric]
    series: list[ReportSeriesPoint]
    breakdowns: dict[str, list[dict]]
    highlights: list[str]
