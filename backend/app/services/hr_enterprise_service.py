from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord, Department, Employee, LeaveRequest, OrgPosition, PayrollRun, User


def employee_portal(db: Session, user: User) -> dict:
    employee = db.scalar(select(Employee).where(Employee.user_id == user.id, Employee.deleted_at.is_(None)))
    employee_scope = employee.id if employee else None
    attendance_query = select(AttendanceRecord).where(AttendanceRecord.company_id == user.company_id, AttendanceRecord.deleted_at.is_(None))
    leave_query = select(LeaveRequest).where(LeaveRequest.company_id == user.company_id, LeaveRequest.deleted_at.is_(None))
    if employee_scope:
        attendance_query = attendance_query.where(AttendanceRecord.employee_id == employee_scope)
        leave_query = leave_query.where(LeaveRequest.employee_id == employee_scope)
    attendance = db.scalars(attendance_query.order_by(AttendanceRecord.work_date.desc()).limit(30))
    leaves = db.scalars(leave_query.order_by(LeaveRequest.created_at.desc()).limit(30))
    payroll = db.scalars(select(PayrollRun).where(PayrollRun.company_id == user.company_id, PayrollRun.deleted_at.is_(None)).order_by(PayrollRun.period.desc()).limit(12))
    return {
        "employee": {"id": employee.id, "full_name": employee.full_name, "job_title": employee.job_title} if employee else None,
        "attendance": [{"id": item.id, "employee_id": item.employee_id, "work_date": item.work_date, "status": item.status, "approval_status": item.approval_status, "location": item.location} for item in attendance],
        "leave_requests": [{"id": item.id, "employee_id": item.employee_id, "leave_type": item.leave_type, "start_date": item.start_date, "end_date": item.end_date, "status": item.status} for item in leaves],
        "payroll_runs": [{"id": item.id, "period": item.period, "status": item.status, "gross_total": float(item.gross_total), "net_total": float(item.net_total)} for item in payroll],
    }


def create_attendance(db: Session, user: User, payload) -> AttendanceRecord:
    employee = db.scalar(select(Employee).where(Employee.id == payload.employee_id, Employee.company_id == user.company_id, Employee.deleted_at.is_(None)))
    if not employee:
        raise ValueError("Trabalhador não encontrado")
    record = AttendanceRecord(
        company_id=user.company_id,
        employee_id=payload.employee_id,
        work_date=payload.work_date,
        check_in_at=payload.check_in_at,
        check_out_at=payload.check_out_at,
        location=payload.location,
        status=payload.status,
        approval_status="pending",
        created_by=user.id,
    )
    db.add(record)
    return record


def create_leave_request(db: Session, user: User, payload) -> LeaveRequest:
    if payload.end_date < payload.start_date:
        raise ValueError("A data final não pode ser anterior à inicial")
    employee = db.scalar(select(Employee).where(Employee.id == payload.employee_id, Employee.company_id == user.company_id, Employee.deleted_at.is_(None)))
    if not employee:
        raise ValueError("Trabalhador não encontrado")
    record = LeaveRequest(
        company_id=user.company_id,
        employee_id=payload.employee_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status="pending",
        created_by=user.id,
    )
    db.add(record)
    return record


def _position_payload(position: OrgPosition, employees: dict[str, Employee], departments: dict[str, Department], children: list[dict] | None = None) -> dict:
    employee = employees.get(position.employee_id or "")
    department = departments.get(position.department_id)
    return {
        "id": position.id,
        "code": position.code,
        "title": position.title,
        "level": position.level,
        "status": position.status,
        "department": {"id": department.id, "name": department.name, "code": department.code} if department else None,
        "employee": {"id": employee.id, "full_name": employee.full_name, "job_title": employee.job_title} if employee else None,
        "supervisor_position_id": position.supervisor_position_id,
        "children": children or [],
    }


def ensure_org_positions(db: Session, user: User) -> None:
    departments = list(db.scalars(select(Department).where(Department.company_id == user.company_id, Department.deleted_at.is_(None)).order_by(Department.code)))
    employees = list(db.scalars(select(Employee).where(Employee.company_id == user.company_id, Employee.deleted_at.is_(None)).order_by(Employee.department_id, Employee.admission_date, Employee.employee_no)))
    existing = {
        item.code: item for item in db.scalars(select(OrgPosition).where(OrgPosition.company_id == user.company_id, OrgPosition.deleted_at.is_(None))).all()
    }
    by_department: dict[str, list[Employee]] = {}
    for employee in employees:
        by_department.setdefault(employee.department_id, []).append(employee)
    for department in departments:
        team = by_department.get(department.id, [])
        supervisor: OrgPosition | None = None
        if team:
            manager = next((employee for employee in team if any(token in employee.job_title.lower() for token in ["manager", "gestor", "chefe", "coordenador", "diretor", "director", "lead"])), team[0])
            code = f"POS-{manager.employee_no}"
            supervisor = existing.get(code)
            if not supervisor:
                supervisor = OrgPosition(
                    company_id=user.company_id,
                    department_id=department.id,
                    employee_id=manager.id,
                    code=code,
                    title=manager.job_title,
                    level=0,
                    status="active",
                    created_by=user.id,
                )
                db.add(supervisor)
                db.flush()
                existing[code] = supervisor
        for employee in team:
            code = f"POS-{employee.employee_no}"
            if code in existing:
                continue
            position = OrgPosition(
                company_id=user.company_id,
                department_id=department.id,
                employee_id=employee.id,
                supervisor_position_id=supervisor.id if supervisor and supervisor.employee_id != employee.id else None,
                code=code,
                title=employee.job_title,
                level=1 if supervisor and supervisor.employee_id != employee.id else 0,
                status="active",
                created_by=user.id,
            )
            db.add(position)
            existing[code] = position
    db.flush()


def org_chart(db: Session, user: User) -> dict:
    ensure_org_positions(db, user)
    positions = list(db.scalars(select(OrgPosition).where(OrgPosition.company_id == user.company_id, OrgPosition.deleted_at.is_(None)).order_by(OrgPosition.level, OrgPosition.code)))
    employee_ids = {position.employee_id for position in positions if position.employee_id}
    department_ids = {position.department_id for position in positions}
    employees = {item.id: item for item in db.scalars(select(Employee).where(Employee.id.in_(employee_ids))).all()} if employee_ids else {}
    departments = {item.id: item for item in db.scalars(select(Department).where(Department.id.in_(department_ids))).all()} if department_ids else {}
    children_by_parent: dict[str | None, list[OrgPosition]] = {}
    for position in positions:
        children_by_parent.setdefault(position.supervisor_position_id, []).append(position)

    def build(position: OrgPosition) -> dict:
        return _position_payload(position, employees, departments, [build(child) for child in children_by_parent.get(position.id, [])])

    roots = [build(position) for position in children_by_parent.get(None, [])]
    return {
        "summary": {
            "positions": len(positions),
            "occupied": sum(1 for position in positions if position.employee_id),
            "vacant": sum(1 for position in positions if not position.employee_id),
            "departments": len(department_ids),
        },
        "positions": [_position_payload(position, employees, departments) for position in positions],
        "tree": roots,
    }


def create_org_position(db: Session, user: User, payload) -> OrgPosition:
    department = db.scalar(select(Department).where(Department.id == payload.department_id, Department.company_id == user.company_id, Department.deleted_at.is_(None)))
    if not department:
        raise ValueError("Departamento não encontrado")
    employee = None
    if payload.employee_id:
        employee = db.scalar(select(Employee).where(Employee.id == payload.employee_id, Employee.company_id == user.company_id, Employee.deleted_at.is_(None)))
        if not employee:
            raise ValueError("Trabalhador não encontrado")
    if payload.supervisor_position_id:
        supervisor = db.scalar(select(OrgPosition).where(OrgPosition.id == payload.supervisor_position_id, OrgPosition.company_id == user.company_id, OrgPosition.deleted_at.is_(None)))
        if not supervisor:
            raise ValueError("Supervisor não encontrado")
    record = OrgPosition(
        company_id=user.company_id,
        department_id=payload.department_id,
        employee_id=employee.id if employee else None,
        supervisor_position_id=payload.supervisor_position_id,
        code=payload.code,
        title=payload.title,
        level=payload.level,
        status="active",
        created_by=user.id,
    )
    db.add(record)
    return record
