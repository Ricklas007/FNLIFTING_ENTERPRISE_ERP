from tests.enterprise_test_utils import client


def test_request_id_and_latency_headers_are_returned():
    api = client()
    response = api.get("/health", headers={"X-Request-ID": "qa-request-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "qa-request-id"
    assert float(response.headers["X-Process-Time-ms"]) >= 0
    api.close()
