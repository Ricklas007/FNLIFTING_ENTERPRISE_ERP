from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_customer_portal_overview_service_request_documents_equipment_and_billing():
    api = client()
    headers = login_headers(api, "cliente@sonangol.co.ao", "Cliente@12345", "client")
    suffix = uuid4().hex[:8]

    overview = api.get("/api/v1/portal/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["client_name"]

    equipment = api.get("/api/v1/operations/equipment", headers=headers)
    certificates = api.get("/api/v1/operations/certificates", headers=headers)
    documents = api.get("/api/v1/management/documents", headers=headers)
    billing = api.get("/api/v1/portal/billing", headers=headers)
    for response in (equipment, certificates, documents, billing):
        assert response.status_code == 200, response.text

    request = api.post(
        "/api/v1/portal/requests",
        headers=headers,
        json={
            "service_type": "inspection",
            "requested_date": date.today().isoformat(),
            "preferred_date": (date.today() + timedelta(days=5)).isoformat(),
            "location": "Base cliente QA",
            "contact_name": "Cliente QA",
            "contact_phone": "+244 922 000 002",
            "priority": "normal",
            "notes": f"Pedido portal QA {suffix}",
        },
    )
    assert request.status_code == 201, request.text
    listed = api.get("/api/v1/portal/requests", headers=headers)
    assert any(item["id"] == request.json()["id"] for item in listed.json())
    api.close()
