from tests.enterprise_test_utils import client, login_headers


def test_external_client_denied_internal_enterprise_admin_data_and_worker_scope():
    api = client()
    client_headers = login_headers(api, "cliente@sonangol.co.ao", "Cliente@12345", "client")
    denied = api.get("/api/v1/enterprise/devices", headers=client_headers)
    assert denied.status_code == 403
    tech_headers = login_headers(api, "tecnico@fnlifting.com", "Tecnico@12345")
    employees = api.get("/api/v1/hr/employees", headers=tech_headers)
    assert employees.status_code == 403
    own = api.get("/api/v1/hr/employees/me", headers=tech_headers)
    assert own.status_code == 200
    api.close()
