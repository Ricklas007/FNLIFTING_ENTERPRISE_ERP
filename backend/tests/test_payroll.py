from tests.enterprise_test_utils import client, login_headers


def test_payroll_decimal_calculation_and_duplicate_prevention():
    api = client()
    headers = login_headers(api)
    run = api.post("/api/v1/enterprise/hr/payroll-runs", headers=headers, json={"period": "2031-01"})
    assert run.status_code == 201, run.text
    assert run.json()["gross_total"] >= run.json()["net_total"]
    duplicate = api.post("/api/v1/enterprise/hr/payroll-runs", headers=headers, json={"period": "2031-01"})
    assert duplicate.status_code == 409
    api.close()
