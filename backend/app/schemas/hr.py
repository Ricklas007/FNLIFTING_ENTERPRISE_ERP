from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    manager_name: str | None = Field(default=None, max_length=180)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    manager_name: str | None = Field(default=None, max_length=180)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class DepartmentOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    manager_name: str | None
    status: str
    employee_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    department_id: str
    user_id: str | None = None
    employee_no: str = Field(min_length=2, max_length=30)
    full_name: str = Field(min_length=3, max_length=180)
    job_title: str = Field(min_length=2, max_length=100)
    birth_date: date | None = None
    bi: str | None = Field(default=None, max_length=40)
    nif: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=260)
    admission_date: date
    contract_type: str = Field(default="permanent", pattern="^(permanent|temporary|service_provider|intern|consultant)$")
    salary: Decimal | None = Field(default=None, ge=0)
    contract_status: str = Field(default="active", pattern="^(active|suspended|ended)$")
    photo_url: str | None = Field(default=None, max_length=400)
    status: str = Field(default="active", pattern="^(active|inactive|on_leave)$")


class EmployeeUpdate(BaseModel):
    department_id: str | None = None
    user_id: str | None = None
    employee_no: str | None = Field(default=None, min_length=2, max_length=30)
    full_name: str | None = Field(default=None, min_length=3, max_length=180)
    job_title: str | None = Field(default=None, min_length=2, max_length=100)
    birth_date: date | None = None
    bi: str | None = Field(default=None, max_length=40)
    nif: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=260)
    admission_date: date | None = None
    contract_type: str | None = Field(default=None, pattern="^(permanent|temporary|service_provider|intern|consultant)$")
    salary: Decimal | None = Field(default=None, ge=0)
    contract_status: str | None = Field(default=None, pattern="^(active|suspended|ended)$")
    photo_url: str | None = Field(default=None, max_length=400)
    status: str | None = Field(default=None, pattern="^(active|inactive|on_leave)$")


class EmployeeOut(BaseModel):
    id: str
    department_id: str
    user_id: str | None
    employee_no: str
    full_name: str
    job_title: str
    birth_date: date | None
    bi: str | None
    nif: str | None
    phone: str | None
    email: str | None
    address: str | None
    admission_date: date
    contract_type: str
    salary: Decimal | None
    contract_status: str
    photo_url: str | None
    status: str
    department: DepartmentOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DailyReportCreate(BaseModel):
    employee_id: str
    department_id: str
    report_date: date
    summary: str = Field(min_length=5, max_length=1000)
    tasks_performed: str = Field(min_length=5, max_length=5000)
    start_time: time | None = None
    end_time: time | None = None
    work_location: str | None = Field(default=None, max_length=180)
    difficulties: str | None = Field(default=None, max_length=3000)
    results_achieved: str | None = Field(default=None, max_length=3000)
    observations: str | None = Field(default=None, max_length=3000)
    work_status: str = Field(default="completed", pattern="^(completed|in_progress|blocked)$")


class DailyReportUpdate(BaseModel):
    summary: str | None = Field(default=None, min_length=5, max_length=1000)
    tasks_performed: str | None = Field(default=None, min_length=5, max_length=5000)
    start_time: time | None = None
    end_time: time | None = None
    work_location: str | None = Field(default=None, max_length=180)
    difficulties: str | None = Field(default=None, max_length=3000)
    results_achieved: str | None = Field(default=None, max_length=3000)
    observations: str | None = Field(default=None, max_length=3000)
    work_status: str | None = Field(default=None, pattern="^(completed|in_progress|blocked)$")


class ReportReview(BaseModel):
    action: str = Field(pattern="^(approve|request_correction)$")
    notes: str | None = Field(default=None, max_length=2000)


class DailyReportOut(BaseModel):
    id: str
    employee_id: str
    department_id: str
    report_date: date
    summary: str
    tasks_performed: str
    start_time: time | None
    end_time: time | None
    work_location: str | None
    difficulties: str | None
    results_achieved: str | None
    observations: str | None
    work_status: str
    status: str
    review_notes: str | None
    reviewed_at: datetime | None
    employee: EmployeeOut
    department: DepartmentOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PerformanceCreate(BaseModel):
    employee_id: str
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    punctuality: Decimal = Field(ge=0, le=5)
    productivity: Decimal = Field(ge=0, le=5)
    work_quality: Decimal = Field(ge=0, le=5)
    task_completion: Decimal = Field(ge=0, le=5)
    reports_score: Decimal = Field(ge=0, le=5)
    supervisor_score: Decimal = Field(ge=0, le=5)
    supervisor_notes: str | None = Field(default=None, max_length=3000)
    status: str = Field(default="published", pattern="^(draft|published)$")

    @field_validator("period")
    @classmethod
    def not_too_old(cls, value: str) -> str:
        if int(value[:4]) < 2020:
            raise ValueError("O período deve ser posterior a 2020")
        return value


class PerformanceOut(BaseModel):
    id: str
    employee_id: str
    period: str
    punctuality: Decimal
    productivity: Decimal
    work_quality: Decimal
    task_completion: Decimal
    reports_score: Decimal
    supervisor_score: Decimal
    overall_score: Decimal
    supervisor_notes: str | None
    status: str
    employee: EmployeeOut
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HRSummary(BaseModel):
    active_employees: int
    departments: int
    pending_reports: int
    reports_this_month: int
    average_performance: float
    employees_on_leave: int
    department_distribution: list[dict[str, str | int]]
    top_performers: list[dict[str, str | float]]

