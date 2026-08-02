from tests.enterprise_test_utils import client


def test_request_id_and_latency_headers_are_returned():
    api = client()
    response = api.get("/health", headers={"X-Request-ID": "qa-request-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "qa-request-id"
    assert float(response.headers["X-Process-Time-ms"]) >= 0
    api.close()


def test_liveness_and_prometheus_metrics_are_exposed():
    api = client()
    live = api.get("/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    metrics = api.get("/metrics")
    assert metrics.status_code == 200
    assert "fnlifting_http_requests_total" in metrics.text
    assert 'path="/live"' in metrics.text
    api.close()
