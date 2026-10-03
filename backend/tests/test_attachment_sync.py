import base64
from uuid import uuid4

from tests.enterprise_test_utils import client, first_employee_id, login_headers


def test_attachment_upload_generates_real_record_that_can_be_synced():
    api = client()
    headers = login_headers(api)
    employee_id = first_employee_id()
    suffix = uuid4().hex[:8]
    data_url = "data:text/plain;base64," + base64.b64encode(b"attachment sync qa").decode("ascii")

    uploaded = api.post(
        f"/api/v1/management/media/entities/employee/{employee_id}",
        headers=headers,
        json={"title": "Sync QA", "category": "document", "file_name": "sync.txt", "file_data_url": data_url},
    )
    assert uploaded.status_code == 201, uploaded.text
    attachment_id = uploaded.json()["id"]

    pushed = api.post(
        "/api/v1/enterprise/sync/push",
        headers=headers,
        json={
            "device_uid": f"media-device-{suffix}",
            "events": [{
                "entity_type": "media_attachment",
                "entity_id": attachment_id,
                "operation": "create",
                "payload": {"checksum_sha256": uploaded.json()["checksum_sha256"], "entity_type": "employee"},
                "cursor": f"media-{suffix}",
            }],
        },
    )
    assert pushed.status_code == 200, pushed.text
    assert pushed.json()["accepted"] == 1
    api.close()
