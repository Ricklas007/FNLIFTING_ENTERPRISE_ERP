from tests.enterprise_test_utils import client, login_headers


def test_all_critical_navigation_endpoints_respond_for_admin_and_rbac_blocks_client():
    api = client()
    admin = login_headers(api)
    client_headers = login_headers(api, "cliente@sonangol.co.ao", "Cliente@12345", "client")

    endpoints = [
        "/api/v1/dashboard/overview",
        "/api/v1/hr/summary",
        "/api/v1/hr/employees",
        "/api/v1/hr/daily-reports",
        "/api/v1/hr/performance",
        "/api/v1/hr/departments?include_inactive=true",
        "/api/v1/operations/summary",
        "/api/v1/operations/clients",
        "/api/v1/operations/equipment",
        "/api/v1/operations/inspections",
        "/api/v1/operations/certificates",
        "/api/v1/fleet/summary",
        "/api/v1/fleet/trucks",
        "/api/v1/fleet/trips",
        "/api/v1/management/assets/summary",
        "/api/v1/management/finance/summary",
        "/api/v1/management/documents",
        "/api/v1/management/audit/summary",
        "/api/v1/system/sync/summary",
        "/api/v1/system/settings",
        "/api/v1/system/ops/readiness",
        "/api/v1/enterprise/overview",
        "/api/v1/enterprise/fleet/command-center",
        "/api/v1/enterprise/ai/automation",
        "/api/v1/enterprise/hr/employee-portal",
        "/api/v1/enterprise/bi/executive",
    ]
    for endpoint in endpoints:
        response = api.get(endpoint, headers=admin)
        assert response.status_code == 200, f"{endpoint}: {response.text}"

    forbidden = api.get("/api/v1/admin/users", headers=client_headers)
    assert forbidden.status_code == 403
    portal = api.get("/api/v1/portal/overview", headers=client_headers)
    assert portal.status_code == 200, portal.text
    api.close()
