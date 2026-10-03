from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import RecordMixin, utcnow


class Department(RecordMixin, Base):
    __tablename__ = "departments"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Employee(RecordMixin, Base):
    __tablename__ = "employees"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    employee_no: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(180), index=True)
    job_title: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    bi: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    nif: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(180), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(260), nullable=True)
    admission_date: Mapped[date] = mapped_column(Date)
    contract_type: Mapped[str] = mapped_column(String(40), default="permanent")
    salary: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    contract_status: Mapped[str] = mapped_column(String(30), default="active")
    photo_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    department: Mapped[Department] = relationship(back_populates="employees")
    daily_reports: Mapped[list["DailyReport"]] = relationship(back_populates="employee")
    performance_reviews: Mapped[list["PerformanceReview"]] = relationship(back_populates="employee")
    technical_signatory: Mapped["TechnicalSignatory | None"] = relationship(back_populates="employee", uselist=False)


class TechnicalSignatory(RecordMixin, Base):
    __tablename__ = "technical_signatories"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), unique=True, index=True)
    inspector_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    qualifications: Mapped[str] = mapped_column(Text)
    employer_name: Mapped[str] = mapped_column(String(180), default="FNLIFTING ANGOLA")
    employer_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stamp_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    can_inspect: Mapped[bool] = mapped_column(Boolean, default=True)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    employee: Mapped[Employee] = relationship(back_populates="technical_signatory")


class Client(RecordMixin, Base):
    __tablename__ = "clients"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    portal_company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    nif: Mapped[str] = mapped_column(String(40), unique=True)
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(String(260), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(180), nullable=True)
    service_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="client")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="client")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="client")


class EquipmentType(RecordMixin, Base):
    __tablename__ = "equipment_types"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    inspection_interval_months: Mapped[int] = mapped_column(Integer, default=12)
    checklist_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="type")


class Equipment(RecordMixin, Base):
    __tablename__ = "equipment"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    equipment_type_id: Mapped[str] = mapped_column(ForeignKey("equipment_types.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    capacity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufacture_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="approved")

    client: Mapped[Client] = relationship(back_populates="equipment")
    type: Mapped[EquipmentType] = relationship(back_populates="equipment")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="equipment")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="equipment")


class Inspection(RecordMixin, Base):
    __tablename__ = "inspections"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey("equipment.id"), index=True)
    inspector_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    inspection_no: Mapped[str] = mapped_column(String(40), unique=True)
    inspection_date: Mapped[date] = mapped_column(Date)
    next_inspection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    defects: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")

    client: Mapped[Client] = relationship(back_populates="inspections")
    equipment: Mapped[Equipment] = relationship(back_populates="inspections")
    inspector: Mapped[Employee | None] = relationship()
    checklist_items: Mapped[list["InspectionChecklistItem"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    photos: Mapped[list["InspectionPhoto"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    certificate: Mapped["Certificate | None"] = relationship(back_populates="inspection", uselist=False)


class InspectionChecklistItem(RecordMixin, Base):
    __tablename__ = "inspection_checklists"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    item_code: Mapped[str] = mapped_column(String(30))
    item_label: Mapped[str] = mapped_column(String(240))
    expected_result: Mapped[str | None] = mapped_column(String(240), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="pass")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="checklist_items")


class InspectionPhoto(RecordMixin, Base):
    __tablename__ = "inspection_photos"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(240), nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="photos")


class Certificate(RecordMixin, Base):
    __tablename__ = "certificates"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey("equipment.id"), index=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"), unique=True, index=True)
    certificate_no: Mapped[str] = mapped_column(String(50), unique=True)
    document_type: Mapped[str] = mapped_column(String(100), default="Certificate of Thorough Examination")
    issued_at: Mapped[date] = mapped_column(Date)
    expires_at: Mapped[date] = mapped_column(Date, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    qr_token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_signatory_id: Mapped[str | None] = mapped_column(ForeignKey("technical_signatories.id"), nullable=True)
    service_order_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    report_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    identification_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    standard_reference: Mapped[str] = mapped_column(String(160), default="BS EN 1492-1:2000+A1:2008")
    colour_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(2), default="C")
    safe_to_use: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")

    client: Mapped[Client] = relationship(back_populates="certificates")
    equipment: Mapped[Equipment] = relationship(back_populates="certificates")
    inspection: Mapped[Inspection] = relationship(back_populates="certificate")
    approver_signatory: Mapped[TechnicalSignatory | None] = relationship()


class Driver(RecordMixin, Base):
    __tablename__ = "drivers"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), unique=True, nullable=True)
    driver_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180), index=True)
    license_number: Mapped[str] = mapped_column(String(60), unique=True)
    license_category: Mapped[str] = mapped_column(String(30))
    license_expires_at: Mapped[date] = mapped_column(Date, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[str] = mapped_column(String(30), default="available", index=True)

    employee: Mapped[Employee | None] = relationship()
    trucks: Mapped[list["Truck"]] = relationship(back_populates="driver")
    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")


class Truck(RecordMixin, Base):
    __tablename__ = "trucks"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)
    plate: Mapped[str] = mapped_column(String(30), unique=True)
    brand: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    manufacture_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truck_type: Mapped[str] = mapped_column(String(60), default="fuel_tanker")
    tank_capacity_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    chassis_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    insurance_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    license_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    inspection_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="available")

    driver: Mapped[Driver | None] = relationship(back_populates="trucks")
    trips: Mapped[list["Trip"]] = relationship(back_populates="truck")
    gps_positions: Mapped[list["GPSPosition"]] = relationship(back_populates="truck", cascade="all, delete-orphan")


class Trip(RecordMixin, Base):
    __tablename__ = "trips"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    truck_id: Mapped[str] = mapped_column(ForeignKey("trucks.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    trip_code: Mapped[str] = mapped_column(String(40), unique=True)
    origin: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(120))
    province: Mapped[str] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quantity_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned")

    truck: Mapped[Truck] = relationship(back_populates="trips")
    driver: Mapped[Driver] = relationship(back_populates="trips")
    client: Mapped[Client | None] = relationship()
    gps_positions: Mapped[list["GPSPosition"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    fuel_records: Mapped[list["FuelRecord"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    incidents: Mapped[list["FleetIncident"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class GPSPosition(RecordMixin, Base):
    __tablename__ = "gps_positions"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    truck_id: Mapped[str] = mapped_column(ForeignKey("trucks.id"), index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_state: Mapped[str] = mapped_column(String(30), default="moving")
    fuel_level_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    truck: Mapped[Truck] = relationship(back_populates="gps_positions")
    trip: Mapped[Trip | None] = relationship(back_populates="gps_positions")


class FuelRecord(RecordMixin, Base):
    __tablename__ = "fuel_records"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    quantity_liters: Mapped[float] = mapped_column(Float)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    location: Mapped[str] = mapped_column(String(180))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    trip: Mapped[Trip] = relationship(back_populates="fuel_records")
    driver: Mapped[Driver] = relationship()


class FleetIncident(RecordMixin, Base):
    __tablename__ = "fleet_incidents"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    incident_type: Mapped[str] = mapped_column(String(50), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)

    trip: Mapped[Trip] = relationship(back_populates="incidents")
    driver: Mapped[Driver] = relationship()


class DailyReport(RecordMixin, Base):
    __tablename__ = "daily_reports"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    summary: Mapped[str] = mapped_column(Text)
    tasks_performed: Mapped[str] = mapped_column(Text)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    work_location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    difficulties: Mapped[str | None] = mapped_column(Text, nullable=True)
    results_achieved: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_status: Mapped[str] = mapped_column(String(30), default="completed")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="daily_reports")
    department: Mapped[Department] = relationship()


class PerformanceReview(RecordMixin, Base):
    __tablename__ = "performance_reviews"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    punctuality: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    productivity: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    work_quality: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    task_completion: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    reports_score: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    supervisor_score: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), index=True)
    supervisor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="published")

    employee: Mapped[Employee] = relationship(back_populates="performance_reviews")


class Expense(RecordMixin, Base):
    __tablename__ = "expenses"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(240))
    vendor: Mapped[str | None] = mapped_column(String(180), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)

    department: Mapped[Department | None] = relationship()
    responsible: Mapped[Employee | None] = relationship()


class Invoice(RecordMixin, Base):
    __tablename__ = "invoices"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="AOA")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)

    client: Mapped[Client] = relationship()
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    receipts: Mapped[list["Receipt"]] = relationship(back_populates="invoice")
    revenues: Mapped[list["Revenue"]] = relationship(back_populates="invoice")


class InvoiceItem(RecordMixin, Base):
    __tablename__ = "invoice_items"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=14)
    line_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class Revenue(RecordMixin, Base):
    __tablename__ = "revenues"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(240))
    service: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)

    client: Mapped[Client] = relationship()
    invoice: Mapped[Invoice | None] = relationship(back_populates="revenues")


class Payment(RecordMixin, Base):
    __tablename__ = "payments"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    method: Mapped[str] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="confirmed", index=True)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class Receipt(RecordMixin, Base):
    __tablename__ = "receipts"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), unique=True, index=True)
    receipt_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issued_at: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="issued", index=True)

    client: Mapped[Client] = relationship()
    invoice: Mapped[Invoice] = relationship(back_populates="receipts")
    payment: Mapped[Payment] = relationship()


class Asset(RecordMixin, Base):
    __tablename__ = "assets"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    asset_code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    acquisition_value: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    depreciation_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=10)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)

    responsible: Mapped[Employee | None] = relationship()
    maintenance_records: Mapped[list["AssetMaintenance"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    transfers: Mapped[list["AssetTransfer"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class AssetMaintenance(RecordMixin, Base):
    __tablename__ = "asset_maintenance"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    maintenance_type: Mapped[str] = mapped_column(String(30), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(180), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    next_maintenance_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True)

    asset: Mapped[Asset] = relationship(back_populates="maintenance_records")


class AssetTransfer(RecordMixin, Base):
    __tablename__ = "asset_transfers"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    from_responsible_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    to_responsible_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    from_location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    to_location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    transfer_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(Text)

    asset: Mapped[Asset] = relationship(back_populates="transfers")
    from_responsible: Mapped[Employee | None] = relationship(foreign_keys=[from_responsible_id])
    to_responsible: Mapped[Employee | None] = relationship(foreign_keys=[to_responsible_id])


class Document(RecordMixin, Base):
    __tablename__ = "documents"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    document_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)

    client: Mapped[Client | None] = relationship()
    employee: Mapped[Employee | None] = relationship()
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(RecordMixin, Base):
    __tablename__ = "document_versions"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(240))
    file_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    document: Mapped[Document] = relationship(back_populates="versions")


class MediaAttachment(RecordMixin, Base):
    __tablename__ = "media_attachments"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(60), default="photo", index=True)
    caption: Mapped[str | None] = mapped_column(String(240), nullable=True)
    file_name: Mapped[str] = mapped_column(String(240))
    file_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class AuditLog(RecordMixin, Base):
    __tablename__ = "audit_logs"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entity_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    before_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    machine_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship()


class Notification(RecordMixin, Base):
    __tablename__ = "notifications"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(30), default="info")
    status: Mapped[str] = mapped_column(String(30), default="unread")


class ClientServiceRequest(RecordMixin, Base):
    __tablename__ = "client_service_requests"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    equipment_id: Mapped[str | None] = mapped_column(ForeignKey("equipment.id"), nullable=True, index=True)
    request_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    service_type: Mapped[str] = mapped_column(String(60), default="inspection", index=True)
    requested_date: Mapped[date] = mapped_column(Date, index=True)
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(220))
    contact_name: Mapped[str] = mapped_column(String(180))
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    response_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship()
    equipment: Mapped[Equipment | None] = relationship()


class SyncQueue(RecordMixin, Base):
    __tablename__ = "sync_queue"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    operation: Mapped[str] = mapped_column(String(20), index=True)
    payload: Mapped[str] = mapped_column(Text)
    base_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncRun(RecordMixin, Base):
    __tablename__ = "sync_runs"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20), default="bidirectional")
    mode: Mapped[str] = mapped_column(String(30), default="local_checkpoint")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pushed_count: Mapped[int] = mapped_column(Integer, default=0)
    pulled_count: Mapped[int] = mapped_column(Integer, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class BackupRecord(RecordMixin, Base):
    __tablename__ = "backups"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    backup_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    file_name: Mapped[str] = mapped_column(String(240))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    format_version: Mapped[str] = mapped_column(String(20), default="FNLBAK-1")
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    includes_files: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="ready", index=True)
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual")
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SystemSetting(RecordMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("company_id", "key", name="uq_settings_company_key"),)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(20), default="string")
    category: Mapped[str] = mapped_column(String(60), default="general", index=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
