from tests.enterprise_test_utils import client, login_headers


def test_customer_message_create_and_list():
    api = client()
    headers = login_headers(api, "cliente@sonangol.co.ao", "Cliente@12345", "client")
    created = api.post("/api/v1/enterprise/customer/messages", headers=headers, json={"subject": "QA portal message", "body": "Pedido de apoio QA", "channel": "portal"})
    assert created.status_code == 201, created.text
    rows = api.get("/api/v1/enterprise/customer/messages", headers=headers)
    assert rows.status_code == 200
    assert any(item["subject"] == "QA portal message" for item in rows.json())
    api.close()
