from datetime import date
from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_payroll_run_creation_and_visibility_in_employee_portal():
    api = client()
    headers = login_headers(api)
    period = f"{date.today().year + 5}-{(int(uuid4().hex[:2], 16) % 12) + 1:02d}"

    created = api.post("/api/v1/enterprise/hr/payroll-runs", headers=headers, json={"period": period})
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["period"] == period
    assert payload["employees"] >= 1
    assert payload["gross_total"] >= payload["net_total"]

    portal = api.get("/api/v1/enterprise/hr/employee-portal", headers=headers)
    assert portal.status_code == 200, portal.text
    assert any(item["period"] == period for item in portal.json()["payroll_runs"])
    api.close()
