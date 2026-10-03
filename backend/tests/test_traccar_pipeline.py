from tests.enterprise_test_utils import client, login_headers


def test_traccar_status_and_provider_pipeline_are_truthful_without_physical_runtime():
    api = client()
    headers = login_headers(api)

    status = api.get("/api/v1/integrations/traccar/status", headers=headers)
    assert status.status_code == 200, status.text
    payload = status.json()
    assert payload["provider"] == "TRACCAR"
    assert payload["status"] in {"CONNECTED", "DISCONNECTED", "AUTH_ERROR"}
    assert payload["configured"] in {True, False}

    test = api.post("/api/v1/integrations/traccar/test", headers=headers)
    assert test.status_code == 200, test.text
    assert test.json()["status"] in {"CONNECTED", "DISCONNECTED", "AUTH_ERROR"}

    providers = api.get("/api/v1/fleet/gps/providers", headers=headers)
    assert providers.status_code == 200, providers.text
    assert any(item["code"] == "TRACCAR" for item in providers.json())
    api.close()
