from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_automation_rule_center_ai_suggestion_generation_and_review():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]

    rule = api.post(
        "/api/v1/enterprise/ai/automation/rules",
        headers=headers,
        json={
            "code": f"QA_RULE_{suffix}",
            "name": "Regra QA de documento pendente",
            "module": "documents",
            "trigger_event": "document.pending",
            "condition": {"approval_status": "pending"},
            "action": {"notify": "documents.manager"},
            "severity": "warning",
        },
    )
    assert rule.status_code == 201, rule.text

    center = api.get("/api/v1/enterprise/ai/automation", headers=headers)
    assert center.status_code == 200, center.text
    assert any(item["code"] == f"QA_RULE_{suffix}" for item in center.json()["rules"])

    generated = api.post("/api/v1/enterprise/ai/assistant/generate", headers=headers)
    assert generated.status_code == 200, generated.text
    suggestions = api.get("/api/v1/enterprise/ai/assistant", headers=headers)
    assert suggestions.status_code == 200, suggestions.text
    if suggestions.json()["suggestions"]:
        suggestion_id = suggestions.json()["suggestions"][0]["id"]
        reviewed = api.patch(f"/api/v1/enterprise/ai/assistant/{suggestion_id}", headers=headers, json={"status": "accepted"})
        assert reviewed.status_code == 200, reviewed.text
    api.close()
