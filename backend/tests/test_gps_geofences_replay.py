from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_device_token_geofence_alert_replay_geojson_and_stream():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]

    driver = api.post("/api/v1/fleet/drivers", headers=headers, json={
        "driver_code": f"DRV-GPS-{suffix}",
        "full_name": "Motorista GPS Token",
        "license_number": f"GPS-TOKEN-{suffix}",
        "license_category": "D",
        "license_expires_at": "2032-12-31",
        "status": "available",
    })
    assert driver.status_code == 201, driver.text
    driver_id = driver.json()["id"]

    truck = api.post("/api/v1/fleet/trucks", headers=headers, json={
        "driver_id": driver_id,
        "plate": f"LD-GPS-{suffix[:2]}-AA",
        "brand": "Volvo",
        "model": "FH GPS",
        "manufacture_year": 2026,
        "truck_type": "fuel_tanker",
        "tank_capacity_liters": 42000,
        "chassis_number": f"GPS-CHASSIS-{suffix}",
        "status": "available",
    })
    assert truck.status_code == 201, truck.text
    truck_id = truck.json()["id"]
    client_id = api.get("/api/v1/operations/clients", headers=headers).json()[0]["id"]
    trip = api.post("/api/v1/fleet/trips", headers=headers, json={
        "truck_id": truck_id,
        "driver_id": driver_id,
        "client_id": client_id,
        "origin": "Luanda",
        "destination": "Terminal Sonils",
        "province": "Luanda",
        "city": "Luanda",
        "status": "in_progress",
    })
    assert trip.status_code == 201, trip.text
    trip_id = trip.json()["id"]

    rule = api.post("/api/v1/fleet/alert-rules", headers=headers, json={
        "code": f"GPS-SPEED-{suffix}",
        "name": "Velocidade teste GPS",
        "alert_type": "speeding",
        "severity": "warning",
        "condition": {"max_speed_kmh": 50},
    })
    assert rule.status_code == 201, rule.text

    geofence = api.post("/api/v1/fleet/geofences", headers=headers, json={
        "name": f"Base Luanda QA {suffix}",
        "geofence_type": "BASE",
        "shape_type": "circle",
        "geometry": {"center": [13.289, -8.839], "radius_meters": 2500},
        "radius_meters": 2500,
    })
    assert geofence.status_code == 201, geofence.text

    device = api.post("/api/v1/fleet/gps/devices", headers=headers, json={
        "device_uid": f"gps-token-qa-{suffix}",
        "label": "Tracker QA 900",
        "truck_id": truck_id,
        "driver_id": driver_id,
        "provider": "pytest-device",
    })
    assert device.status_code == 201, device.text
    token = device.json()["token"]
    assert token.startswith("fnlgps.")

    unauthorized = api.post("/api/v1/fleet/gps/ingest", json={
        "event_id": "evt-unauthorized",
        "latitude": -8.839,
        "longitude": 13.289,
    })
    assert unauthorized.status_code == 401

    payload = {
        "event_id": f"evt-gps-token-{suffix}",
        "trip_id": trip_id,
        "latitude": -8.839,
        "longitude": 13.289,
        "speed_kmh": 72,
        "heading": 180,
        "accuracy_meters": 7,
        "ignition_status": "on",
        "fuel_level_percent": 78,
        "odometer_km": 12001,
        "timestamp": "2026-07-17T03:00:00+00:00",
    }
    first = api.post("/api/v1/fleet/gps/ingest", headers={"X-GPS-Device-Token": token}, json=payload)
    duplicate = api.post("/api/v1/fleet/gps/ingest", headers={"X-GPS-Device-Token": token}, json=payload)
    assert first.status_code == 201, first.text
    assert duplicate.status_code == 201, duplicate.text
    assert first.json()["integration_event_id"] == duplicate.json()["integration_event_id"]
    assert first.json()["gps_position_id"]
    assert first.json()["alerts_created"] >= 2
    assert first.json()["geofence_events_created"] >= 1

    live = api.get("/api/v1/fleet/gps/live", headers=headers)
    assert live.status_code == 200, live.text
    assert any(item["truck_id"] == truck_id and item["latitude"] == -8.839 for item in live.json())

    alerts = api.get("/api/v1/fleet/alerts", headers=headers)
    assert alerts.status_code == 200, alerts.text
    alert_types = {item["alert_type"] for item in alerts.json()}
    assert {"speeding", "geofence_enter"} <= alert_types

    replay = api.get(f"/api/v1/fleet/gps/replay?truck_id={truck_id}", headers=headers)
    assert replay.status_code == 200, replay.text
    assert replay.json()["count"] >= 1
    assert replay.json()["bounds"]

    geojson = api.get(f"/api/v1/fleet/gps/export.geojson?truck_id={truck_id}", headers=headers)
    assert geojson.status_code == 200, geojson.text
    assert geojson.json()["type"] == "FeatureCollection"
    assert geojson.json()["features"]

    stream = api.get("/api/v1/fleet/gps/stream", headers=headers)
    assert stream.status_code == 200, stream.text
    assert "event: gps_live" in stream.text

    resolved = api.post(f"/api/v1/fleet/alerts/{alerts.json()[0]['id']}/resolve", headers=headers)
    assert resolved.status_code == 200, resolved.text
    api.close()
