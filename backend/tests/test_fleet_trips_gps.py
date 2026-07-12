from tests.enterprise_test_utils import client, login_headers


def test_gps_ingest_invalid_duplicate_and_speeding_alert():
    api = client()
    headers = login_headers(api)
    center = api.get("/api/v1/enterprise/fleet/command-center", headers=headers)
    truck_id = center.json()["trucks"][0]["id"]
    invalid = api.post("/api/v1/enterprise/gps/ingest", headers=headers, json={"truck_id": truck_id, "latitude": 99, "longitude": 13, "payload": {}})
    assert invalid.status_code == 422
    event = {"provider": "pytest-gps", "truck_id": truck_id, "latitude": -8.83, "longitude": 13.28, "speed_kmh": 110, "payload": {"event_id": "gps-dup-1"}}
    first = api.post("/api/v1/enterprise/gps/ingest", headers=headers, json=event)
    second = api.post("/api/v1/enterprise/gps/ingest", headers=headers, json=event)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    updated = api.get("/api/v1/enterprise/fleet/command-center", headers=headers)
    assert any(item["command_type"] == "speeding_alert" for item in updated.json()["commands"])
    api.close()
