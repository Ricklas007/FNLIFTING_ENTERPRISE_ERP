from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import DailyReport, Department, Employee, PerformanceReview, User
from app.schemas.auth import MessageResponse
from app.schemas.hr import (
    DailyReportCreate,
    DailyReportOut,
    DailyReportUpdate,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    HRSummary,
    PerformanceCreate,
    PerformanceOut,
    ReportReview,
)


router = APIRouter(prefix="/hr", tags=["Recursos Humanos"])


def department_out(db: Session, department: Department) -> DepartmentOut:
    result = DepartmentOut.model_validate(department)
    result.employee_count = db.scalar(
        select(func.count(Employee.id)).where(
            Employee.department_id == department.id,
            Employee.deleted_at.is_(None),
        )
    ) or 0
    return result


def get_department(db: Session, department_id: str, company_id: str) -> Department:
    department = db.scalar(select(Department).where(
        Department.id == department_id,
        Department.company_id == company_id,
        Department.deleted_at.is_(None),
    ))
    if not department:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    return department


def get_employee(db: Session, employee_id: str, company_id: str) -> Employee:
    employee = db.scalar(
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.id == employee_id, Employee.company_id == company_id, Employee.deleted_at.is_(None))
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")
    return employee


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


@router.get("/summary", response_model=HRSummary)
def hr_summary(
    user: User = Depends(require_permission("hr.view")),
    db: Session = Depends(get_db),
):
    company_id = user.company_id
    active = db.scalar(select(func.count(Employee.id)).where(
        Employee.company_id == company_id, Employee.status == "active", Employee.deleted_at.is_(None)
    )) or 0
    department_total = db.scalar(select(func.count(Department.id)).where(
        Department.company_id == company_id, Department.status == "active", Department.deleted_at.is_(None)
    )) or 0
    pending = db.scalar(select(func.count(DailyReport.id)).where(
        DailyReport.company_id == company_id, DailyReport.status == "pending", DailyReport.deleted_at.is_(None)
    )) or 0
    today = date.today()
    month_start = today.replace(day=1)
    next_month = date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
    monthly_reports = db.scalar(select(func.count(DailyReport.id)).where(
        DailyReport.company_id == company_id,
        DailyReport.report_date >= month_start,
        DailyReport.report_date < next_month,
        DailyReport.deleted_at.is_(None),
    )) or 0
    average = db.scalar(select(func.avg(PerformanceReview.overall_score)).where(
        PerformanceReview.company_id == company_id,
        PerformanceReview.status == "published",
        PerformanceReview.deleted_at.is_(None),
    )) or 0
    on_leave = db.scalar(select(func.count(Employee.id)).where(
        Employee.company_id == company_id, Employee.status == "on_leave", Employee.deleted_at.is_(None)
    )) or 0
    distribution_rows = db.execute(
        select(Department.name, func.count(Employee.id))
        .outerjoin(Employee, (Employee.department_id == Department.id) & Employee.deleted_at.is_(None))
        .where(Department.company_id == company_id, Department.deleted_at.is_(None))
        .group_by(Department.id)
        .order_by(func.count(Employee.id).desc())
    ).all()
    top_rows = db.execute(
        select(Employee.full_name, Employee.job_title, PerformanceReview.overall_score)
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .where(PerformanceReview.company_id == company_id, PerformanceReview.status == "published")
        .order_by(PerformanceReview.overall_score.desc())
        .limit(5)
    ).all()
    return HRSummary(
        active_employees=active,
        departments=department_total,
        pending_reports=pending,
        reports_this_month=monthly_reports,
        average_performance=round(float(average), 2),
        employees_on_leave=on_leave,
        department_distribution=[{"name": name, "value": count} for name, count in distribution_rows],
        top_performers=[{"name": name, "job_title": title, "score": float(score)} for name, title, score in top_rows],
    )


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    include_inactive: bool = False,
    user: User = Depends(require_permission("departments.view")),
    db: Session = Depends(get_db),
):
    query = select(Department).where(Department.company_id == user.company_id, Department.deleted_at.is_(None))
    if not include_inactive:
        query = query.where(Department.status == "active")
    records = db.scalars(query.order_by(Department.name)).all()
    return [department_out(db, record) for record in records]


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    user: User = Depends(require_permission("departments.manage")),
    db: Session = Depends(get_db),
):
    department = Department(
        company_id=user.company_id,
        created_by=user.id,
        **payload.model_dump(),
    )
    db.add(department)
    commit_or_conflict(db, "Já existe um departamento com este código")
    db.refresh(department)
    return department_out(db, department)


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    user: User = Depends(require_permission("departments.manage")),
    db: Session = Depends(get_db),
):
    department = get_department(db, department_id, user.company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    department.updated_by = user.id
    commit_or_conflict(db, "Já existe um departamento com este código")
    db.refresh(department)
    return department_out(db, department)


@router.delete("/departments/{department_id}", response_model=MessageResponse)
def delete_department(
    department_id: str,
    user: User = Depends(require_permission("departments.manage")),
    db: Session = Depends(get_db),
):
    department = get_department(db, department_id, user.company_id)
    employees = db.scalar(select(func.count(Employee.id)).where(
        Employee.department_id == department.id, Employee.deleted_at.is_(None)
    )) or 0
    if employees:
        raise HTTPException(status_code=409, detail="Transfira os trabalhadores antes de eliminar o departamento")
    department.deleted_at = datetime.now(timezone.utc)
    department.updated_by = user.id
    db.commit()
    return MessageResponse(message="Departamento removido")


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    search: str | None = Query(default=None, max_length=100),
    department_id: str | None = None,
    employee_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_permission("employees.view")),
    db: Session = Depends(get_db),
):
    query = (
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.company_id == user.company_id, Employee.deleted_at.is_(None))
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Employee.full_name.ilike(term), Employee.employee_no.ilike(term), Employee.job_title.ilike(term)))
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if employee_status:
        query = query.where(Employee.status == employee_status)
    return list(db.scalars(query.order_by(Employee.full_name)).all())


@router.get("/employees/me", response_model=EmployeeOut)
def my_employee_record(
    user: User = Depends(require_permission("daily_reports.submit")),
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.user_id == user.id, Employee.company_id == user.company_id, Employee.deleted_at.is_(None))
    )
    if not employee:
        raise HTTPException(status_code=404, detail="A sua conta ainda não está associada a um trabalhador")
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def employee_detail(
    employee_id: str,
    user: User = Depends(require_permission("employees.view")),
    db: Session = Depends(get_db),
):
    return get_employee(db, employee_id, user.company_id)


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    user: User = Depends(require_permission("employees.manage")),
    db: Session = Depends(get_db),
):
    get_department(db, payload.department_id, user.company_id)
    employee = Employee(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(employee)
    commit_or_conflict(db, "Número, BI, NIF, email ou conta de utilizador já associado")
    return get_employee(db, employee.id, user.company_id)


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    user: User = Depends(require_permission("employees.manage")),
    db: Session = Depends(get_db),
):
    employee = get_employee(db, employee_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("department_id"):
        get_department(db, changes["department_id"], user.company_id)
    for field, value in changes.items():
        setattr(employee, field, value)
    employee.updated_by = user.id
    commit_or_conflict(db, "Número, BI, NIF, email ou conta de utilizador já associado")
    return get_employee(db, employee.id, user.company_id)


@router.delete("/employees/{employee_id}", response_model=MessageResponse)
def delete_employee(
    employee_id: str,
    user: User = Depends(require_permission("employees.manage")),
    db: Session = Depends(get_db),
):
    employee = get_employee(db, employee_id, user.company_id)
    employee.deleted_at = datetime.now(timezone.utc)
    employee.status = "inactive"
    employee.updated_by = user.id
    db.commit()
    return MessageResponse(message="Trabalhador arquivado com sucesso")


def can_manage_report(user: User, employee: Employee) -> bool:
    permissions = user.permission_codes
    return "*" in permissions or "daily_reports.review" in permissions or employee.user_id == user.id


@router.get("/daily-reports", response_model=list[DailyReportOut])
def list_daily_reports(
    report_status: str | None = Query(default=None, alias="status"),
    employee_id: str | None = None,
    department_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(require_permission("daily_reports.view")),
    db: Session = Depends(get_db),
):
    query = (
        select(DailyReport)
        .options(
            selectinload(DailyReport.employee).selectinload(Employee.department),
            selectinload(DailyReport.department),
        )
        .where(DailyReport.company_id == user.company_id, DailyReport.deleted_at.is_(None))
    )
    if "*" not in user.permission_codes and "daily_reports.review" not in user.permission_codes:
        query = query.join(Employee, Employee.id == DailyReport.employee_id).where(Employee.user_id == user.id)
    if report_status:
        query = query.where(DailyReport.status == report_status)
    if employee_id:
        query = query.where(DailyReport.employee_id == employee_id)
    if department_id:
        query = query.where(DailyReport.department_id == department_id)
    if date_from:
        query = query.where(DailyReport.report_date >= date_from)
    if date_to:
        query = query.where(DailyReport.report_date <= date_to)
    return list(db.scalars(query.order_by(DailyReport.report_date.desc(), DailyReport.created_at.desc())).unique().all())


@router.post("/daily-reports", response_model=DailyReportOut, status_code=status.HTTP_201_CREATED)
def create_daily_report(
    payload: DailyReportCreate,
    user: User = Depends(require_permission("daily_reports.submit")),
    db: Session = Depends(get_db),
):
    employee = get_employee(db, payload.employee_id, user.company_id)
    if not can_manage_report(user, employee):
        raise HTTPException(status_code=403, detail="Só pode submeter o seu próprio relatório")
    if payload.department_id != employee.department_id:
        raise HTTPException(status_code=422, detail="O departamento não corresponde ao trabalhador")
    exists = db.scalar(select(DailyReport.id).where(
        DailyReport.employee_id == employee.id,
        DailyReport.report_date == payload.report_date,
        DailyReport.deleted_at.is_(None),
    ))
    if exists:
        raise HTTPException(status_code=409, detail="Já existe um relatório deste trabalhador para a data")
    report = DailyReport(
        company_id=user.company_id,
        created_by=user.id,
        status="pending",
        **payload.model_dump(),
    )
    db.add(report)
    db.commit()
    return db.scalar(
        select(DailyReport)
        .options(selectinload(DailyReport.employee).selectinload(Employee.department), selectinload(DailyReport.department))
        .where(DailyReport.id == report.id)
    )


@router.patch("/daily-reports/{report_id}", response_model=DailyReportOut)
def update_daily_report(
    report_id: str,
    payload: DailyReportUpdate,
    user: User = Depends(require_permission("daily_reports.submit")),
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(DailyReport)
        .options(selectinload(DailyReport.employee).selectinload(Employee.department), selectinload(DailyReport.department))
        .where(DailyReport.id == report_id, DailyReport.company_id == user.company_id, DailyReport.deleted_at.is_(None))
    )
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if not can_manage_report(user, report.employee):
        raise HTTPException(status_code=403, detail="Sem acesso a este relatório")
    if report.status == "approved" and "daily_reports.review" not in user.permission_codes and "*" not in user.permission_codes:
        raise HTTPException(status_code=409, detail="Um relatório aprovado não pode ser alterado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    report.status = "pending"
    report.updated_by = user.id
    db.commit()
    return report


@router.post("/daily-reports/{report_id}/review", response_model=DailyReportOut)
def review_daily_report(
    report_id: str,
    payload: ReportReview,
    user: User = Depends(require_permission("daily_reports.review")),
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(DailyReport)
        .options(selectinload(DailyReport.employee).selectinload(Employee.department), selectinload(DailyReport.department))
        .where(DailyReport.id == report_id, DailyReport.company_id == user.company_id, DailyReport.deleted_at.is_(None))
    )
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    report.status = "approved" if payload.action == "approve" else "correction_requested"
    report.review_notes = payload.notes
    report.reviewed_by = user.id
    report.reviewed_at = datetime.now(timezone.utc)
    report.updated_by = user.id
    db.commit()
    return report


@router.get("/performance", response_model=list[PerformanceOut])
def list_performance(
    period: str | None = None,
    department_id: str | None = None,
    user: User = Depends(require_permission("performance.view")),
    db: Session = Depends(get_db),
):
    query = (
        select(PerformanceReview)
        .options(selectinload(PerformanceReview.employee).selectinload(Employee.department))
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .where(PerformanceReview.company_id == user.company_id, PerformanceReview.deleted_at.is_(None))
    )
    if period:
        query = query.where(PerformanceReview.period == period)
    if department_id:
        query = query.where(Employee.department_id == department_id)
    return list(db.scalars(query.order_by(PerformanceReview.overall_score.desc())).unique().all())


@router.post("/performance", response_model=PerformanceOut, status_code=status.HTTP_201_CREATED)
def create_performance(
    payload: PerformanceCreate,
    user: User = Depends(require_permission("performance.manage")),
    db: Session = Depends(get_db),
):
    get_employee(db, payload.employee_id, user.company_id)
    exists = db.scalar(select(PerformanceReview.id).where(
        PerformanceReview.employee_id == payload.employee_id,
        PerformanceReview.period == payload.period,
        PerformanceReview.deleted_at.is_(None),
    ))
    if exists:
        raise HTTPException(status_code=409, detail="Já existe uma avaliação para este trabalhador e período")
    values = payload.model_dump()
    scores = [Decimal(values[key]) for key in (
        "punctuality", "productivity", "work_quality", "task_completion", "reports_score", "supervisor_score"
    )]
    overall = (sum(scores) / Decimal(len(scores))) * Decimal(20)
    review = PerformanceReview(
        company_id=user.company_id,
        created_by=user.id,
        overall_score=overall.quantize(Decimal("0.01")),
        **values,
    )
    db.add(review)
    db.commit()
    return db.scalar(
        select(PerformanceReview)
        .options(selectinload(PerformanceReview.employee).selectinload(Employee.department))
        .where(PerformanceReview.id == review.id)
    )
