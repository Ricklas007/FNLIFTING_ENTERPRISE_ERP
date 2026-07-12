from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import SyncQueue, User
from tests.enterprise_test_utils import client, login_headers


def test_sync_push_duplicate_pull_status_and_conflict_resolution():
    api = client()
    headers = login_headers(api)
    device = api.post("/api/v1/enterprise/devices/register", headers=headers, json={"device_uid": "qa-sync-device", "name": "QA Sync", "platform": "pytest", "capabilities": ["sync"]})
    assert device.status_code == 201, device.text

    payload = {"device_uid": "qa-sync-device", "events": [{"entity_type": "qa_entity", "entity_id": "QA-1", "operation": "upsert", "payload": {"value": 1}, "cursor": "qa-cursor-1"}]}
    pushed = api.post("/api/v1/enterprise/sync/push", headers=headers, json=payload)
    assert pushed.status_code == 200, pushed.text
    duplicate = api.post("/api/v1/enterprise/sync/push", headers=headers, json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicates"] >= 1

    pulled = api.get("/api/v1/enterprise/sync/pull", headers=headers)
    assert pulled.status_code == 200
    assert any(item["entity_id"] == "QA-1" for item in pulled.json()["events"])
    status = api.get("/api/v1/enterprise/sync/status", headers=headers)
    assert status.status_code == 200

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@fnlifting.com"))
        conflict = SyncQueue(company_id=admin.company_id, entity_type="qa_entity", entity_id="QA-CONFLICT", operation="update", payload="{}", status="conflict", conflict_payload='{"remote":true}', created_by=admin.id)
        db.add(conflict)
        db.commit()
        conflict_id = conflict.id
    conflicts = api.get("/api/v1/enterprise/sync/conflicts", headers=headers)
    assert conflicts.status_code == 200
    assert any(item["id"] == conflict_id for item in conflicts.json())
    resolved = api.post(f"/api/v1/enterprise/sync/conflicts/{conflict_id}/resolve", headers=headers, json={"strategy": "merge", "merged_payload": {"value": "merged"}})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "pending"
    assert "merged" in resolved.json()["payload"]
    api.close()
