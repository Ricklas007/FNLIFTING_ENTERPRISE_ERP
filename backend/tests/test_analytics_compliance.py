from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


def test_executive_bi_real_data_and_compliance_create():
    api = client()
    headers = login_headers(api)
    bi = api.get("/api/v1/enterprise/bi/executive", headers=headers)
    assert bi.status_code == 200
    assert any(item["key"] == "revenue" and item["value"] >= 0 for item in bi.json()["scorecards"])
    requirement_code = f"QA-COMP-{uuid4().hex[:8].upper()}"
    compliance = api.post("/api/v1/enterprise/compliance", headers=headers, json={"code": requirement_code, "title": "QA compliance evidence", "category": "QA", "authority": "Internal", "risk_level": "medium"})
    assert compliance.status_code == 201, compliance.text
    rows = api.get("/api/v1/enterprise/compliance", headers=headers)
    assert any(item["code"] == requirement_code for item in rows.json())
    api.close()
