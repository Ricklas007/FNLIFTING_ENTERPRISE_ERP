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
    api.close()
