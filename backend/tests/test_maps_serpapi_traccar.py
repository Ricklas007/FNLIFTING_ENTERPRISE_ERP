import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from app.api.routes import integrations, maps
from tests.enterprise_test_utils import client, login_headers


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_maplibre_dark_style_is_functional():
    style_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "maps" / "styles" / "fnl-dark.json"
    style = json.loads(style_path.read_text(encoding="utf-8"))
    assert style["version"] == 8
    assert style["sources"]["carto-dark"]["type"] == "raster"
    assert style["sources"]["carto-dark"]["tiles"]
    assert any(layer["id"] == "carto-dark-raster" and layer["type"] == "raster" for layer in style["layers"])


def test_maps_status_exposes_online_serpapi_and_google_provider_state(monkeypatch):
    monkeypatch.delenv("SERPAPI_ENABLED", raising=False)
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    api = client()
    headers = login_headers(api)

    response = api.get("/api/v1/maps/status", headers=headers)

    assert response.status_code == 200, response.text
    providers = response.json()["providers"]
    assert providers["ONLINE_RASTER"]["available"] is True
    assert providers["ONLINE_RASTER"]["style"] == "carto_dark_raster"
    assert providers["SERPAPI_PLACE_SEARCH"]["available"] is False
    assert providers["SERPAPI_PLACE_SEARCH"]["role"] == "AUXILIARY_PLACE_SEARCH"
    assert "GOOGLE_ONLINE" in providers
    api.close()


def test_serpapi_test_endpoint_reports_not_configured_and_connected(monkeypatch):
    api = client()
    headers = login_headers(api)
    monkeypatch.delenv("SERPAPI_ENABLED", raising=False)
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    maps._SERPAPI_CALLS.clear()
    maps._SERPAPI_CACHE.clear()

    missing = api.post("/api/v1/integrations/serpapi/test", headers=headers)
    assert missing.status_code == 200, missing.text
    assert missing.json()["status"] == "NOT_CONFIGURED"

    monkeypatch.setenv("SERPAPI_ENABLED", "true")
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key")
    monkeypatch.setenv("SERPAPI_RATE_LIMIT", "20")

    def fake_urlopen(request, timeout=8):
        assert "engine=google_maps" in request.full_url
        assert "api_key=test-serpapi-key" in request.full_url
        return _FakeResponse({
            "local_results": [{
                "place_id": "place-test",
                "title": "Luanda",
                "gps_coordinates": {"latitude": -8.839, "longitude": 13.289},
            }]
        })

    monkeypatch.setattr(maps, "urlopen", fake_urlopen)
    connected = api.post("/api/v1/integrations/serpapi/test", headers=headers)
    assert connected.status_code == 200, connected.text
    assert connected.json()["status"] == "CONNECTED"
    assert connected.json()["configured"] is True
    api.close()


def test_serpapi_missing_key_normalization_timeout_and_rate_limit(monkeypatch):
    api = client()
    headers = login_headers(api)
    monkeypatch.delenv("SERPAPI_ENABLED", raising=False)
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    maps._SERPAPI_CALLS.clear()

    missing = api.get("/api/v1/maps/places/search?query=Luanda", headers=headers)
    assert missing.status_code == 503

    normalized = maps._normalize_serpapi_place({
        "place_id": "abc",
        "title": "Terminal Luanda",
        "type": "terminal logístico",
        "address": "Luanda",
        "gps_coordinates": {"latitude": -8.839, "longitude": 13.289},
        "rating": "4.5",
        "reviews": "12",
    }, maps.now_iso())
    assert normalized is not None
    assert normalized.title == "Terminal Luanda"
    assert normalized.latitude == -8.839
    assert maps._normalize_serpapi_place({"title": "sem coordenadas"}, maps.now_iso()) is None

    monkeypatch.setenv("SERPAPI_ENABLED", "true")
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key")
    monkeypatch.delenv("SERPAPI_RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.setenv("SERPAPI_RATE_LIMIT", "1")
    maps._SERPAPI_CALLS.clear()
    maps._check_serpapi_rate("user-rate")
    with pytest.raises(Exception) as exc:
        maps._check_serpapi_rate("user-rate")
    assert getattr(exc.value, "status_code", None) == 429

    maps._SERPAPI_CALLS.clear()

    def timeout_urlopen(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(maps, "urlopen", timeout_urlopen)
    timeout = api.get("/api/v1/maps/places/search?query=Luanda", headers=headers)
    assert timeout.status_code == 504
    api.close()


def test_serpapi_endpoint_normalizes_google_maps_results(monkeypatch):
    api = client()
    headers = login_headers(api)
    monkeypatch.setenv("SERPAPI_ENABLED", "true")
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key")
    monkeypatch.setenv("SERPAPI_RATE_LIMIT_PER_MINUTE", "20")
    maps._SERPAPI_CALLS.clear()

    def fake_urlopen(request, timeout=8):
        assert "engine=google_maps" in request.full_url
        assert "api_key=test-serpapi-key" in request.full_url
        return _FakeResponse({
            "local_results": [{
                "place_id": "place-1",
                "title": "Oficina FNL Luanda",
                "type": "oficina mecânica",
                "address": "Luanda, Angola",
                "gps_coordinates": {"latitude": -8.91, "longitude": 13.23},
            }]
        })

    monkeypatch.setattr(maps, "urlopen", fake_urlopen)
    response = api.get("/api/v1/maps/places/search?query=oficina&latitude=-8.8&longitude=13.2&zoom=10", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()[0]["title"] == "Oficina FNL Luanda"
    assert response.json()[0]["source"] == "SERPAPI_GOOGLE_MAPS"
    api.close()


def test_operational_places_persist_serpapi_result_with_geofence():
    api = client()
    headers = login_headers(api)
    payload = {
        "title": "Terminal Logístico Luanda",
        "category": "terminal logístico",
        "address": "Luanda",
        "latitude": -8.839,
        "longitude": 13.289,
        "source": "SERPAPI_GOOGLE_MAPS",
        "external_id": "serpapi-terminal-luanda",
        "retrieved_at": "2026-08-02T04:00:00Z",
        "metadata": {"rating": 4.6, "reviews": 12},
        "create_geofence": True,
        "geofence_type": "TERMINAL",
        "radius_meters": 150,
    }

    created = api.post("/api/v1/fleet/operational-places", json=payload, headers=headers)

    assert created.status_code == 201, created.text
    data = created.json()
    assert data["title"] == payload["title"]
    assert data["source"] == "SERPAPI_GOOGLE_MAPS"
    assert data["metadata"]["rating"] == 4.6
    assert data["geofence_id"]

    updated_payload = {**payload, "address": "Luanda - Porto", "metadata": {"rating": 4.7}}
    updated = api.post("/api/v1/fleet/operational-places", json=updated_payload, headers=headers)
    assert updated.status_code == 201, updated.text
    assert updated.json()["id"] == data["id"]
    assert updated.json()["address"] == "Luanda - Porto"

    listed = api.get("/api/v1/fleet/operational-places?status=active&q=Terminal", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()].count(data["id"]) == 1

    geofences = api.get("/api/v1/fleet/geofences", headers=headers)
    assert geofences.status_code == 200, geofences.text
    assert any(item["id"] == data["geofence_id"] and item["geofence_type"] == "TERMINAL" for item in geofences.json())
    api.close()


def test_traccar_disconnected_auth_devices_import_and_link(monkeypatch):
    api = client()
    headers = login_headers(api)
    monkeypatch.delenv("TRACCAR_ENABLED", raising=False)
    monkeypatch.delenv("TRACCAR_BASE_URL", raising=False)
    monkeypatch.delenv("TRACCAR_URL", raising=False)

    status_response = api.get("/api/v1/integrations/traccar/status", headers=headers)
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "DISCONNECTED"

    devices_without_config = api.get("/api/v1/integrations/traccar/devices", headers=headers)
    assert devices_without_config.status_code == 503

    monkeypatch.setenv("TRACCAR_ENABLED", "true")
    monkeypatch.setenv("TRACCAR_BASE_URL", "https://traccar.example.test")

    def auth_error_urlopen(*args, **kwargs):
        raise HTTPError("https://traccar.example.test/api/server", 401, "Unauthorized", None, None)

    monkeypatch.setattr(integrations, "urlopen", auth_error_urlopen)
    auth_status = api.get("/api/v1/integrations/traccar/status", headers=headers)
    assert auth_status.status_code == 200, auth_status.text
    assert auth_status.json()["status"] == "AUTH_ERROR"

    unique_id = "TRC-UNIT-TEST-001"

    def fake_traccar_urlopen(request, timeout=8):
        if request.full_url.endswith("/api/server"):
            return _FakeResponse({"version": "mock"})
        if request.full_url.endswith("/api/devices"):
            return _FakeResponse([{
                "id": 9001,
                "name": "Tracker QA Traccar",
                "uniqueId": unique_id,
                "status": "online",
                "category": "truck",
            }])
        return _FakeResponse({})

    monkeypatch.setattr(integrations, "urlopen", fake_traccar_urlopen)
    devices = api.get("/api/v1/integrations/traccar/devices", headers=headers)
    assert devices.status_code == 200, devices.text
    assert devices.json()[0]["unique_id"] == unique_id

    imported = api.post("/api/v1/integrations/traccar/import-devices", headers=headers, json={"device_ids": ["9001"]})
    assert imported.status_code == 201, imported.text

    gps_devices = api.get("/api/v1/fleet/gps/devices", headers=headers)
    device = next(item for item in gps_devices.json() if item["device_uid"] == unique_id)
    truck_id = api.get("/api/v1/fleet/trucks", headers=headers).json()[0]["id"]

    linked = api.post("/api/v1/integrations/traccar/link-device", headers=headers, json={"device_id": device["id"], "truck_id": truck_id})
    assert linked.status_code == 200, linked.text
    assert linked.json()["unique_id"] == unique_id
    api.close()
