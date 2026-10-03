from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Employee, User
from tests.enterprise_test_utils import client, login_headers


def _employee_for(email: str) -> Employee:
    with SessionLocal() as db:
        employee = db.scalar(select(Employee).join(User, User.id == Employee.user_id).where(User.email == email, Employee.deleted_at.is_(None)))
        assert employee
        return employee


def test_worker_portal_allows_technician_to_submit_own_report_and_view_portal():
    api = client()
    headers = login_headers(api, "tecnico@fnlifting.com", "Tecnico@12345", "staff")
    employee = _employee_for("tecnico@fnlifting.com")
    suffix = uuid4().hex[:8]
    report_date = date.today() + timedelta(days=4600 + int(suffix[:4], 16) % 500)

    report = api.post(
        "/api/v1/hr/daily-reports",
        headers=headers,
        json={
            "employee_id": employee.id,
            "department_id": employee.department_id,
            "report_date": report_date.isoformat(),
            "summary": "Relatório próprio no portal",
            "tasks_performed": "Submissão por perfil técnico sem permissões administrativas",
            "work_location": "Campo QA",
            "work_status": "completed",
        },
    )
    assert report.status_code == 201, report.text
    portal = api.get("/api/v1/enterprise/hr/employee-portal", headers=headers)
    assert portal.status_code == 200, portal.text
    payload = portal.json()
    assert payload["employee"]["full_name"] == employee.full_name
    assert "attendance" in payload and "leave_requests" in payload and "payroll_runs" in payload
    api.close()
