from datetime import date, timedelta

from tests.enterprise_test_utils import client, first_employee_id, login_headers


def test_attendance_and_leave_request_validation():
    api = client()
    headers = login_headers(api)
    employee_id = first_employee_id()
    today = date.today().isoformat()
    attendance = api.post("/api/v1/enterprise/hr/attendance", headers=headers, json={"employee_id": employee_id, "work_date": today, "location": "Base QA", "status": "present"})
    assert attendance.status_code == 201, attendance.text
    invalid_leave = api.post("/api/v1/enterprise/hr/leave-requests", headers=headers, json={"employee_id": employee_id, "start_date": (date.today() + timedelta(days=3)).isoformat(), "end_date": date.today().isoformat()})
    assert invalid_leave.status_code == 422
    leave = api.post("/api/v1/enterprise/hr/leave-requests", headers=headers, json={"employee_id": employee_id, "start_date": date.today().isoformat(), "end_date": (date.today() + timedelta(days=2)).isoformat(), "reason": "QA"})
    assert leave.status_code == 201, leave.text
    portal = api.get("/api/v1/enterprise/hr/employee-portal", headers=headers)
    assert portal.status_code == 200
    api.close()
