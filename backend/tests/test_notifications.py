from tests.enterprise_test_utils import client, login_headers


def test_notifications_generate_dedupe_and_mark_read():
    api = client()
    headers = login_headers(api)
    before = api.get("/api/v1/enterprise/notifications", headers=headers)
    assert before.status_code == 200
    api.post("/api/v1/enterprise/notifications/generate-demo", headers=headers)
    api.post("/api/v1/enterprise/notifications/generate-demo", headers=headers)
    rows = api.get("/api/v1/enterprise/notifications", headers=headers)
    assert rows.status_code == 200
    assert rows.json()
    unread = next(item for item in rows.json() if item["status"] == "unread")
    marked = api.post(f"/api/v1/enterprise/notifications/{unread['id']}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["status"] == "read"
    api.close()
