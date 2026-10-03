from datetime import date
from uuid import uuid4

from tests.enterprise_test_utils import client, first_approver_signatory_id, first_client_id, first_equipment_type_id, login_headers


def test_certificate_lifecycle_from_approved_inspection_to_issued_pdf_and_public_validation():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]
    equipment = api.post(
        "/api/v1/operations/equipment",
        headers=headers,
        json={
            "client_id": first_client_id(),
            "equipment_type_id": first_equipment_type_id(),
            "code": f"QA-CERT-EQP-{suffix}",
            "name": "Lifting sling certificate QA",
            "manufacturer": "FNLIFTING",
            "model": "CERT-QA",
            "serial_number": f"CERT-SER-{suffix}",
            "capacity": "10 t",
            "manufacture_year": 2026,
            "location": "Luanda",
            "status": "approved",
        },
    )
    assert equipment.status_code == 201, equipment.text

    inspection = api.post(
        "/api/v1/operations/inspections",
        headers=headers,
        json={
            "equipment_id": equipment.json()["id"],
            "inspection_date": date.today().isoformat(),
            "location": "Luanda",
            "status": "approved",
            "conclusion": "Aprovado para uso.",
            "checklist_items": [{"item_code": "A", "item_label": "Inspeção visual", "expected_result": "Conforme", "result": "pass"}],
        },
    )
    assert inspection.status_code == 201, inspection.text

    draft = api.post(
        "/api/v1/operations/certificates",
        headers=headers,
        json={
            "inspection_id": inspection.json()["id"],
            "approver_signatory_id": first_approver_signatory_id(),
            "standard_reference": "BS EN 1492-1:2000+A1:2008",
            "colour_code": "Blue/Black",
            "safe_to_use": True,
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "draft"

    issued = api.post(f"/api/v1/operations/certificates/{draft.json()['id']}/issue", headers=headers)
    assert issued.status_code == 200, issued.text
    issued_payload = issued.json()
    assert issued_payload["status"] == "issued"
    assert issued_payload["pdf_available"] is True

    pdf = api.get(f"/api/v1/operations/certificates/{issued_payload['id']}/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")

    public = api.get(f"/api/v1/public/certificates/{issued_payload['qr_token']}")
    assert public.status_code == 200, public.text
    assert public.json()["certificate_status"] == "issued"
    assert public.json()["valid"] is True
    api.close()
