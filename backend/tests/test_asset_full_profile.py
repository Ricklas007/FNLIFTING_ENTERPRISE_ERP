from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, first_employee_id, login_headers


def test_asset_profile_maintenance_and_transfer_workflow():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]
    employee_id = first_employee_id()

    created = api.post(
        "/api/v1/management/assets",
        headers=headers,
        json={
            "asset_code": f"QA-PAT-{suffix}",
            "name": "Equipamento patrimonial QA",
            "category": "Ferramentas",
            "brand": "FNL",
            "model": "QA-1",
            "serial_number": f"PAT-SER-{suffix}",
            "acquisition_date": date.today().isoformat(),
            "acquisition_value": "150000",
            "location": "Luanda",
            "responsible_id": employee_id,
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]

    maintenance = api.post(
        f"/api/v1/management/assets/{asset_id}/maintenance",
        headers=headers,
        json={
            "maintenance_type": "preventive",
            "scheduled_date": (date.today() + timedelta(days=10)).isoformat(),
            "provider": "Oficina QA",
            "cost": "12500",
            "description": "Manutenção preventiva automatizada",
            "status": "scheduled",
        },
    )
    assert maintenance.status_code == 201, maintenance.text

    transfer = api.post(
        f"/api/v1/management/assets/{asset_id}/transfers",
        headers=headers,
        json={"to_responsible_id": employee_id, "to_location": "Benguela", "transfer_date": date.today().isoformat(), "reason": "Realocação QA"},
    )
    assert transfer.status_code == 201, transfer.text
    updated = api.get("/api/v1/management/assets", headers=headers)
    assert any(item["id"] == asset_id and item["transfer_count"] >= 1 for item in updated.json())
    api.close()
