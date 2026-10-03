from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, first_department_id, first_employee_id, login_headers


def test_worker_profile_daily_report_review_and_worker_portal_access():
    api = client()
    admin = login_headers(api)
    suffix = uuid4().hex[:8]
    department_id = first_department_id()

    created = api.post(
        "/api/v1/hr/employees",
        headers=admin,
        json={
            "department_id": department_id,
            "employee_no": f"QA-WRK-{suffix}",
            "full_name": f"Trabalhador QA {suffix}",
            "job_title": "Técnico QA",
            "admission_date": date.today().isoformat(),
            "contract_type": "permanent",
            "salary": "250000",
            "contract_status": "active",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    employee_id = created.json()["id"]

    updated = api.patch(
        f"/api/v1/hr/employees/{employee_id}",
        headers=admin,
        json={"phone": "+244 923 000 001", "address": "Luanda · QA"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["phone"] == "+244 923 000 001"

    report_date = date.today() + timedelta(days=4000 + int(suffix[:4], 16) % 500)
    report = api.post(
        "/api/v1/hr/daily-reports",
        headers=admin,
        json={
            "employee_id": employee_id,
            "department_id": department_id,
            "report_date": report_date.isoformat(),
            "summary": "Validação de perfil completo",
            "tasks_performed": "Cadastro, anexos, relatório e revisão funcional",
            "work_location": "Base QA",
            "work_status": "completed",
        },
    )
    assert report.status_code == 201, report.text
    reviewed = api.post(f"/api/v1/hr/daily-reports/{report.json()['id']}/review", headers=admin, json={"action": "approve", "notes": "Validado"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "approved"

    technician = login_headers(api, "tecnico@fnlifting.com", "Tecnico@12345", "staff")
    own_portal = api.get("/api/v1/enterprise/hr/employee-portal", headers=technician)
    assert own_portal.status_code == 200, own_portal.text
    assert "attendance" in own_portal.json()
    api.close()
