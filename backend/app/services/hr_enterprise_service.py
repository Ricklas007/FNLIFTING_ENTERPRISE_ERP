from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord, Employee, LeaveRequest, PayrollRun, User


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
