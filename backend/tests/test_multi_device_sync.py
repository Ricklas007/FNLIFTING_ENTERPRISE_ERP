from uuid import uuid4

from tests.enterprise_test_utils import client, first_employee_id, login_headers


def test_multi_device_registration_push_pull_and_duplicate_cursor():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]
    device_uid = f"qa-device-{suffix}"

    registered = api.post(
        "/api/v1/enterprise/devices/register",
        headers=headers,
        json={"device_uid": device_uid, "name": "Tablet QA", "platform": "android", "app_version": "0.12.1", "capabilities": ["offline", "media"]},
    )
    assert registered.status_code == 201, registered.text

    employee_id = first_employee_id()
    event = {
        "entity_type": "employee",
        "entity_id": employee_id,
        "operation": "update",
        "payload": {"field": "last_sync_probe", "value": suffix},
        "cursor": f"cursor-{suffix}",
    }
    first = api.post("/api/v1/enterprise/sync/push", headers=headers, json={"device_uid": device_uid, "events": [event]})
    second = api.post("/api/v1/enterprise/sync/push", headers=headers, json={"device_uid": device_uid, "events": [event]})
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["accepted"] == 1
    assert second.json()["duplicates"] == 1

    pulled = api.get("/api/v1/enterprise/sync/pull", headers=headers)
    assert pulled.status_code == 200, pulled.text
    assert any(item["cursor"] == event["cursor"] for item in pulled.json()["events"])
    status = api.get("/api/v1/enterprise/sync/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["events"] >= 1
    api.close()
