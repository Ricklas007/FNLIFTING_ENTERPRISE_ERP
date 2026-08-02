from uuid import uuid4

from .enterprise_test_utils import client, login_headers


def test_phase_15_gps_pilot_simulation_and_pdf_report():
    api = client()
    headers = login_headers(api)

    checklist = api.get("/api/v1/fleet/gps/pilot/checklist", headers=headers)
    assert checklist.status_code == 200, checklist.text
    checklist_payload = checklist.json()
    assert checklist_payload["hardware_required"] is True
    assert "HTTP" in checklist_payload["methods"]
    assert checklist_payload["simulator"]["provider"] == "HTTP_TRACKER_SIMULATOR"
    assert any(item["field"] == "imei" for item in checklist_payload["items"])

    run_code = f"PYTEST-GPS-PILOT-{uuid4().hex[:8]}"
    response = api.post("/api/v1/fleet/gps/pilot/simulate", headers=headers, json={"run_code": run_code, "include_report": True})
    assert response.status_code == 201, response.text
    payload = response.json()

    assert payload["run_code"] == run_code
    assert payload["positions_created"] >= 6
    assert payload["replay_count"] == payload["positions_created"]
    assert payload["stops_count"] >= 2
    assert payload["alerts_created"] >= 2
    assert payload["geofence_events_created"] >= 2
    assert payload["offline_buffer"]["simulated"] is True
    assert payload["offline_buffer"]["queued_points"] == 2
    assert payload["offline_buffer"]["flush_order_validated"] is True
    assert payload["security"]["device_token_hash_present"] is True
    assert payload["security"]["token_returned_in_response"] is False
    assert payload["security"]["dedupe_validated"] is True
    assert "GPS_SIMULATED_VALIDATED" in payload["classifications"]
    assert "GPS_PHYSICAL_PENDING_HARDWARE" in payload["classifications"]
    assert payload["pdf_report"]["generated"] is True
    assert payload["pdf_report"]["file_name"].endswith(".pdf")
    assert payload["pdf_report"]["size_bytes"] > 1200
    assert len(payload["pdf_report"]["sha256"]) == 64

    replay = api.get(f"/api/v1/fleet/gps/replay?trip_id={payload['trip_id']}", headers=headers)
    assert replay.status_code == 200, replay.text
    replay_payload = replay.json()
    assert replay_payload["count"] == payload["positions_created"]
    assert replay_payload["bounds"] is not None

    alerts = api.get("/api/v1/fleet/alerts?status=open", headers=headers)
    assert alerts.status_code == 200, alerts.text
    assert any(item["trip_id"] == payload["trip_id"] for item in alerts.json())

    pdf = api.get(payload["pdf_report"]["download_url"], headers=headers)
    assert pdf.status_code == 200, pdf.text[:200]
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
