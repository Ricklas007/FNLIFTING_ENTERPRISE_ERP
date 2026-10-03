from datetime import date
from uuid import uuid4

from tests.enterprise_test_utils import client, first_client_id, first_equipment_type_id, login_headers


def test_equipment_profile_create_update_and_inspection_validation():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]
    client_id = first_client_id()
    type_id = first_equipment_type_id()

    created = api.post(
        "/api/v1/operations/equipment",
        headers=headers,
        json={
            "client_id": client_id,
            "equipment_type_id": type_id,
            "code": f"QA-EQP-{suffix}",
            "name": "Webbing Sling QA",
            "manufacturer": "FNLIFTING QA",
            "model": "WS-QA",
            "serial_number": f"SER-QA-{suffix}",
            "capacity": "5 t",
            "manufacture_year": 2026,
            "location": "Luanda",
            "status": "pending",
        },
    )
    assert created.status_code == 201, created.text
    equipment_id = created.json()["id"]

    updated = api.patch(f"/api/v1/operations/equipment/{equipment_id}", headers=headers, json={"status": "approved", "location": "Malanje"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["location"] == "Malanje"

    invalid = api.post(
        "/api/v1/operations/inspections",
        headers=headers,
        json={
            "equipment_id": equipment_id,
            "inspection_date": date.today().isoformat(),
            "location": "Malanje",
            "status": "approved",
            "checklist_items": [{"item_code": "QA1", "item_label": "Carga nominal", "expected_result": "Conforme", "result": "fail"}],
        },
    )
    assert invalid.status_code == 422

    inspection = api.post(
        "/api/v1/operations/inspections",
        headers=headers,
        json={
            "equipment_id": equipment_id,
            "inspection_date": date.today().isoformat(),
            "location": "Malanje",
            "status": "approved",
            "conclusion": "Equipamento apto para operação QA.",
            "checklist_items": [{"item_code": "QA1", "item_label": "Carga nominal", "expected_result": "Conforme", "result": "pass"}],
        },
    )
    assert inspection.status_code == 201, inspection.text
    assert inspection.json()["status"] == "approved"
    api.close()
