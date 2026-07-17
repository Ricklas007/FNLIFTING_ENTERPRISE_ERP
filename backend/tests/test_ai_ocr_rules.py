from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_ai_providers_ocr_job_and_rule_creation():
    api = client()
    headers = login_headers(api)
    providers = api.get("/api/v1/enterprise/ai/providers", headers=headers)
    assert providers.status_code == 200
    assert any(item["mode"] in {"local", "cloud"} for item in providers.json())
    ocr = api.post("/api/v1/enterprise/ai/ocr/jobs", headers=headers, json={"source_filename": "qa-certificate.pdf", "sample_text": "SWL 2T Inspector QA"})
    assert ocr.status_code == 201, ocr.text
    assert ocr.json()["status"] == "review_required"
    rule_code = f"QA_RULE_{uuid4().hex[:8].upper()}"
    rule = api.post("/api/v1/enterprise/ai/automation/rules", headers=headers, json={"code": rule_code, "name": "QA blocking rule", "module": "qa", "trigger_event": "qa.event", "condition": {"value": 1}, "action": {"notify": True}, "severity": "critical"})
    assert rule.status_code == 201, rule.text
    center = api.get("/api/v1/enterprise/ai/automation", headers=headers)
    assert any(item["code"] == rule_code for item in center.json()["rules"])
    generated = api.post("/api/v1/enterprise/ai/assistant/generate", headers=headers)
    assert generated.status_code == 200, generated.text
    assistant = api.get("/api/v1/enterprise/ai/assistant", headers=headers)
    assert assistant.status_code == 200, assistant.text
    suggestions = assistant.json()["suggestions"]
    assert any(item["source_type"] == "ocr_job" for item in suggestions)
    selected = next(item for item in suggestions if item["source_type"] == "ocr_job")
    reviewed = api.patch(
        f"/api/v1/enterprise/ai/assistant/{selected['id']}",
        headers=headers,
        json={"status": "edited", "recommendation": "Validar OCR QA e anexar observação antes da aprovação."},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "edited"
    api.close()
