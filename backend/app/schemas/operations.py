from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    nif: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=260)
    contact_person: str | None = Field(default=None, max_length=180)
    service_notes: str | None = Field(default=None, max_length=3000)
    status: str = Field(default="active", pattern="^(active|inactive|prospect)$")


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    nif: str | None = Field(default=None, min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=260)
    contact_person: str | None = Field(default=None, max_length=180)
    service_notes: str | None = Field(default=None, max_length=3000)
    status: str | None = Field(default=None, pattern="^(active|inactive|prospect)$")


class ClientOut(BaseModel):
    id: str
    name: str
    nif: str
    email: str | None
    phone: str | None
    address: str | None
    contact_person: str | None
    service_notes: str | None
    status: str
    equipment_count: int = 0
    certificate_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EquipmentTypeOut(BaseModel):
    id: str
    code: str
    name: str
    inspection_interval_months: int
    checklist_template: str | None
    status: str
    model_config = ConfigDict(from_attributes=True)


class EquipmentCreate(BaseModel):
    client_id: str
    equipment_type_id: str
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=180)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    capacity: str | None = Field(default=None, max_length=80)
    manufacture_year: int | None = Field(default=None, ge=1900, le=2100)
    location: str | None = Field(default=None, max_length=180)
    status: str = Field(default="pending", pattern="^(approved|rejected|with_defect|pending|out_of_service)$")


class EquipmentUpdate(BaseModel):
    client_id: str | None = None
    equipment_type_id: str | None = None
    code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    capacity: str | None = Field(default=None, max_length=80)
    manufacture_year: int | None = Field(default=None, ge=1900, le=2100)
    location: str | None = Field(default=None, max_length=180)
    status: str | None = Field(default=None, pattern="^(approved|rejected|with_defect|pending|out_of_service)$")


class EquipmentOut(BaseModel):
    id: str
    client_id: str
    equipment_type_id: str
    code: str
    name: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    capacity: str | None
    manufacture_year: int | None
    location: str | None
    status: str
    client: ClientOut
    type: EquipmentTypeOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChecklistItemInput(BaseModel):
    item_code: str = Field(min_length=1, max_length=30)
    item_label: str = Field(min_length=2, max_length=240)
    expected_result: str | None = Field(default=None, max_length=240)
    result: str = Field(default="pass", pattern="^(pass|fail|na)$")
    notes: str | None = Field(default=None, max_length=2000)


class ChecklistItemOut(ChecklistItemInput):
    id: str
    model_config = ConfigDict(from_attributes=True)


class InspectionCreate(BaseModel):
    equipment_id: str
    inspector_id: str | None = None
    inspection_date: date
    next_inspection_date: date | None = None
    location: str | None = Field(default=None, max_length=180)
    defects: str | None = Field(default=None, max_length=4000)
    recommendations: str | None = Field(default=None, max_length=4000)
    conclusion: str | None = Field(default=None, max_length=4000)
    status: str = Field(default="pending", pattern="^(approved|rejected|with_defect|pending|out_of_service)$")
    checklist_items: list[ChecklistItemInput] = Field(default_factory=list, max_length=100)


class InspectionUpdate(BaseModel):
    inspector_id: str | None = None
    inspection_date: date | None = None
    next_inspection_date: date | None = None
    location: str | None = Field(default=None, max_length=180)
    defects: str | None = Field(default=None, max_length=4000)
    recommendations: str | None = Field(default=None, max_length=4000)
    conclusion: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, pattern="^(approved|rejected|with_defect|pending|out_of_service)$")
    checklist_items: list[ChecklistItemInput] | None = Field(default=None, max_length=100)


class InspectorOut(BaseModel):
    id: str
    full_name: str
    employee_no: str
    job_title: str
    model_config = ConfigDict(from_attributes=True)


class TechnicalSignatoryCreate(BaseModel):
    employee_id: str
    inspector_code: str = Field(min_length=2, max_length=40)
    qualifications: str = Field(min_length=2, max_length=3000)
    employer_name: str = Field(default="FNLIFTING ANGOLA", max_length=180)
    employer_address: str | None = Field(default=None, max_length=300)
    signature_data_url: str | None = Field(default=None, max_length=4_000_000)
    stamp_data_url: str | None = Field(default=None, max_length=4_000_000)
    can_inspect: bool = True
    can_approve: bool = False
    status: str = Field(default="active", pattern="^(active|inactive)$")


class TechnicalSignatoryUpdate(BaseModel):
    inspector_code: str | None = Field(default=None, min_length=2, max_length=40)
    qualifications: str | None = Field(default=None, min_length=2, max_length=3000)
    employer_name: str | None = Field(default=None, max_length=180)
    employer_address: str | None = Field(default=None, max_length=300)
    signature_data_url: str | None = Field(default=None, max_length=4_000_000)
    stamp_data_url: str | None = Field(default=None, max_length=4_000_000)
    can_inspect: bool | None = None
    can_approve: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class TechnicalSignatoryOut(BaseModel):
    id: str
    employee_id: str
    inspector_code: str
    qualifications: str
    employer_name: str
    employer_address: str | None
    can_inspect: bool
    can_approve: bool
    status: str
    signature_available: bool = False
    stamp_available: bool = False
    employee: InspectorOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InspectionOut(BaseModel):
    id: str
    client_id: str
    equipment_id: str
    inspector_id: str | None
    inspection_no: str
    inspection_date: date
    next_inspection_date: date | None
    location: str | None
    defects: str | None
    recommendations: str | None
    conclusion: str | None
    status: str
    client: ClientOut
    equipment: EquipmentOut
    inspector: InspectorOut | None
    checklist_items: list[ChecklistItemOut]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CertificateCreate(BaseModel):
    inspection_id: str
    document_type: str = Field(default="Certificate of Thorough Examination", max_length=100)
    approver_signatory_id: str | None = None
    service_order_no: str | None = Field(default=None, max_length=60)
    report_no: str | None = Field(default=None, max_length=60)
    identification_no: str | None = Field(default=None, max_length=100)
    standard_reference: str = Field(default="BS EN 1492-1:2000+A1:2008", max_length=160)
    colour_code: str | None = Field(default=None, max_length=60)
    reason_code: str = Field(default="C", pattern="^[A-E]$")
    safe_to_use: bool = True


class CertificateUpdate(BaseModel):
    document_type: str | None = Field(default=None, max_length=100)
    approver_signatory_id: str | None = None
    service_order_no: str | None = Field(default=None, max_length=60)
    report_no: str | None = Field(default=None, max_length=60)
    identification_no: str | None = Field(default=None, max_length=100)
    standard_reference: str | None = Field(default=None, max_length=160)
    colour_code: str | None = Field(default=None, max_length=60)
    reason_code: str | None = Field(default=None, pattern="^[A-E]$")
    safe_to_use: bool | None = None


class CertificateOut(BaseModel):
    id: str
    client_id: str
    equipment_id: str
    inspection_id: str
    certificate_no: str
    document_type: str
    issued_at: date
    expires_at: date
    revision: int
    qr_token: str
    approver_signatory_id: str | None
    service_order_no: str | None
    report_no: str | None
    identification_no: str | None
    standard_reference: str
    colour_code: str | None
    reason_code: str
    safe_to_use: bool
    status: str
    pdf_available: bool = False
    client: ClientOut
    equipment: EquipmentOut
    inspection: InspectionOut
    approver_signatory: TechnicalSignatoryOut | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PublicCertificateOut(BaseModel):
    certificate_no: str
    document_type: str
    client_name: str
    equipment_code: str
    equipment_name: str
    issued_at: date
    expires_at: date
    inspection_status: str
    certificate_status: str
    valid: bool
    validation_hash: str | None = None


class OperationsSummary(BaseModel):
    active_clients: int
    equipment_total: int
    inspections_pending: int
    inspections_approved: int
    certificates_issued: int
    certificates_expiring: int
    equipment_by_status: list[dict[str, str | int]]
