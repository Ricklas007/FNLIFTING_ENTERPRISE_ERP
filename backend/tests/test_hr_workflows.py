from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, first_employee_id, login_headers


def test_attendance_and_leave_request_validation():
    api = client()
    headers = login_headers(api)
    employee_id = first_employee_id()
    base_date = date.today() + timedelta(days=30 + int(uuid4().hex[:4], 16) % 3000)
    attendance = api.post("/api/v1/enterprise/hr/attendance", headers=headers, json={"employee_id": employee_id, "work_date": base_date.isoformat(), "location": "Base QA", "status": "present"})
    assert attendance.status_code == 201, attendance.text
    invalid_leave = api.post("/api/v1/enterprise/hr/leave-requests", headers=headers, json={"employee_id": employee_id, "start_date": (base_date + timedelta(days=3)).isoformat(), "end_date": base_date.isoformat()})
    assert invalid_leave.status_code == 422
    leave = api.post("/api/v1/enterprise/hr/leave-requests", headers=headers, json={"employee_id": employee_id, "start_date": base_date.isoformat(), "end_date": (base_date + timedelta(days=2)).isoformat(), "reason": "QA"})
    assert leave.status_code == 201, leave.text
    portal = api.get("/api/v1/enterprise/hr/employee-portal", headers=headers)
    assert portal.status_code == 200
    org = api.get("/api/v1/enterprise/hr/org-chart", headers=headers)
    assert org.status_code == 200, org.text
    payload = org.json()
    assert payload["summary"]["positions"] >= 1
    assert payload["positions"][0]["department"]
    assert "tree" in payload
    api.close()
