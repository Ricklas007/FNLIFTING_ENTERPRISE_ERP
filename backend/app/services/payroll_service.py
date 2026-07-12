from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee, PayrollItem, PayrollRun, User


def create_payroll_run(db: Session, user: User, period: str) -> PayrollRun:
    exists = db.scalar(select(PayrollRun).where(PayrollRun.company_id == user.company_id, PayrollRun.period == period, PayrollRun.deleted_at.is_(None)))
    if exists:
        raise ValueError("Já existe processamento salarial para este período")
    employees = list(db.scalars(select(Employee).where(Employee.company_id == user.company_id, Employee.status == "active", Employee.deleted_at.is_(None))))
    run = PayrollRun(company_id=user.company_id, period=period, status="draft", created_by=user.id)
    db.add(run)
    db.flush()
    gross_total = Decimal("0")
    deduction_total = Decimal("0")
    for employee in employees:
        gross = Decimal(employee.salary or 0)
        if gross < 0:
            raise ValueError("Salário negativo não é permitido")
        deductions = (gross * Decimal("0.08")).quantize(Decimal("0.01")) if gross else Decimal("0")
        net = gross - deductions
        gross_total += gross
        deduction_total += deductions
        db.add(PayrollItem(company_id=user.company_id, payroll_run_id=run.id, employee_id=employee.id, gross_pay=gross, deductions=deductions, net_pay=net, created_by=user.id))
    run.gross_total = gross_total
    run.deduction_total = deduction_total
    run.net_total = gross_total - deduction_total
    return run
