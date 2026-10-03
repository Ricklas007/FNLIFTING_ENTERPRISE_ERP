from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.operations import ClientOut


class PersonRef(BaseModel):
    id: str
    full_name: str
    employee_no: str
    job_title: str
    model_config = ConfigDict(from_attributes=True)


class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    acquisition_date: date | None = None
    acquisition_value: Decimal = Field(ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    depreciation_rate: Decimal = Field(default=10, ge=0, le=100)
    location: str | None = Field(default=None, max_length=180)
    responsible_id: str | None = None
    notes: str | None = Field(default=None, max_length=3000)
    status: str = Field(default="active", pattern="^(active|maintenance|transferred|retired|lost)$")


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    acquisition_date: date | None = None
    acquisition_value: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    depreciation_rate: Decimal | None = Field(default=None, ge=0, le=100)
    location: str | None = Field(default=None, max_length=180)
    responsible_id: str | None = None
    notes: str | None = Field(default=None, max_length=3000)
    status: str | None = Field(default=None, pattern="^(active|maintenance|transferred|retired|lost)$")


class AssetOut(AssetCreate):
    id: str
    responsible: PersonRef | None
    maintenance_count: int = 0
    transfer_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MaintenanceCreate(BaseModel):
    maintenance_type: str = Field(pattern="^(preventive|corrective|inspection)$")
    scheduled_date: date
    completed_date: date | None = None
    provider: str | None = Field(default=None, max_length=180)
    cost: Decimal | None = Field(default=None, ge=0)
    description: str = Field(min_length=2, max_length=3000)
    next_maintenance_date: date | None = None
    status: str = Field(default="scheduled", pattern="^(scheduled|in_progress|completed|cancelled)$")


class MaintenanceOut(MaintenanceCreate):
    id: str
    asset_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TransferCreate(BaseModel):
    to_responsible_id: str | None = None
    to_location: str | None = Field(default=None, max_length=180)
    transfer_date: date
    reason: str = Field(min_length=2, max_length=3000)


class TransferOut(BaseModel):
    id: str
    asset_id: str
    from_responsible_id: str | None
    to_responsible_id: str | None
    from_location: str | None
    to_location: str | None
    transfer_date: date
    reason: str
    from_responsible: PersonRef | None
    to_responsible: PersonRef | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssetSummary(BaseModel):
    total_assets: int
    active_assets: int
    in_maintenance: int
    maintenance_due: int
    acquisition_value: Decimal
    current_value: Decimal
    by_category: list[dict[str, str | int]]


class ExpenseCreate(BaseModel):
    department_id: str | None = None
    responsible_id: str | None = None
    category: str = Field(min_length=2, max_length=80)
    amount: Decimal = Field(gt=0)
    transaction_date: date
    description: str = Field(min_length=2, max_length=240)
    vendor: str | None = Field(default=None, max_length=180)
    due_date: date | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    status: str = Field(default="pending", pattern="^(pending|approved|paid|rejected)$")


class ExpenseOut(ExpenseCreate):
    id: str
    department_name: str | None = None
    responsible_name: str | None = None
    approved_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RevenueCreate(BaseModel):
    client_id: str
    invoice_id: str | None = None
    amount: Decimal = Field(gt=0)
    transaction_date: date
    description: str = Field(min_length=2, max_length=240)
    service: str | None = Field(default=None, max_length=160)
    payment_method: str | None = Field(default=None, max_length=50)
    reference: str | None = Field(default=None, max_length=100)
    status: str = Field(default="pending", pattern="^(pending|paid|cancelled)$")


class RevenueOut(RevenueCreate):
    id: str
    client: ClientOut
    paid_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvoiceItemInput(BaseModel):
    description: str = Field(min_length=2, max_length=240)
    quantity: Decimal = Field(default=1, gt=0)
    unit_price: Decimal = Field(gt=0)
    tax_rate: Decimal = Field(default=14, ge=0, le=100)


class InvoiceCreate(BaseModel):
    client_id: str
    issue_date: date
    due_date: date
    currency: str = Field(default="AOA", max_length=10)
    notes: str | None = Field(default=None, max_length=3000)
    status: str = Field(default="issued", pattern="^(draft|issued|partial|paid|overdue|cancelled)$")
    items: list[InvoiceItemInput] = Field(min_length=1, max_length=100)


class InvoiceItemOut(InvoiceItemInput):
    id: str
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class InvoiceOut(BaseModel):
    id: str
    client_id: str
    invoice_no: str
    issue_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal = 0
    balance_due: Decimal = 0
    notes: str | None
    status: str
    pdf_available: bool = False
    client: ClientOut
    items: list[InvoiceItemOut]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal = Field(gt=0)
    method: str = Field(min_length=2, max_length=50)
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=3000)


class ReceiptOut(BaseModel):
    id: str
    client_id: str
    invoice_id: str
    payment_id: str
    receipt_no: str
    issued_at: date
    amount: Decimal
    status: str
    pdf_available: bool = False
    client: ClientOut
    invoice: InvoiceOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FinanceSummary(BaseModel):
    revenue_total: Decimal
    expense_total: Decimal
    profit: Decimal
    receivables: Decimal
    payables: Decimal
    invoices_open: int
    expenses_pending: int
    cash_flow: list[dict[str, str | float]]
    expenses_by_category: list[dict[str, str | float]]


class DocumentCreate(BaseModel):
    client_id: str | None = None
    employee_id: str | None = None
    title: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    valid_until: date | None = None
    approval_status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    file_name: str = Field(min_length=1, max_length=240)
    file_data_url: str = Field(min_length=10, max_length=15_000_000)
    change_notes: str | None = Field(default=None, max_length=2000)


class DocumentUpdate(BaseModel):
    client_id: str | None = None
    employee_id: str | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=3000)
    valid_until: date | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class DocumentReview(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    notes: str | None = Field(default=None, max_length=2000)


class DocumentVersionCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=240)
    file_data_url: str = Field(min_length=10, max_length=15_000_000)
    change_notes: str | None = Field(default=None, max_length=2000)


class DocumentVersionOut(BaseModel):
    id: str
    version_no: int
    file_name: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    change_notes: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    id: str
    client_id: str | None
    employee_id: str | None
    document_no: str
    title: str
    category: str
    description: str | None
    current_version: int
    valid_until: date | None
    approval_status: str
    status: str
    client: ClientOut | None
    employee: PersonRef | None
    versions: list[DocumentVersionOut]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MediaAttachmentOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    title: str
    category: str
    caption: str | None
    file_name: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    thumbnail_available: bool = False
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MediaAttachmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    category: str = Field(default="photo", min_length=2, max_length=60)
    caption: str | None = Field(default=None, max_length=240)
    file_name: str = Field(min_length=1, max_length=240)
    file_data_url: str = Field(min_length=10, max_length=15_000_000)


class AuditLogOut(BaseModel):
    id: str
    user_id: str | None
    user_name: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    entity_label: str | None
    before_data: str | None
    after_data: str | None
    ip_address: str | None
    machine_name: str | None
    description: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditSummary(BaseModel):
    total_events: int
    events_today: int
    active_users: int
    sensitive_actions: int
    by_action: list[dict[str, str | int]]
