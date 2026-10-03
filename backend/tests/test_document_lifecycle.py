import base64
from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, first_client_id, first_employee_id, login_headers


def _text_data_url(text: str) -> str:
    return "data:text/plain;base64," + base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_document_lifecycle_preview_revision_reject_and_approve():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]
    created = api.post(
        "/api/v1/management/documents",
        headers=headers,
        json={
            "client_id": first_client_id(),
            "employee_id": first_employee_id(),
            "title": f"Relatório RH QA {suffix}",
            "category": "RH",
            "description": "Documento de validação de ciclo completo",
            "valid_until": (date.today() + timedelta(days=365)).isoformat(),
            "file_name": f"relatorio-{suffix}.txt",
            "file_data_url": _text_data_url("versao inicial"),
            "change_notes": "Criação automatizada",
        },
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    download = api.get(f"/api/v1/management/documents/{document_id}/download", headers=headers)
    assert download.status_code == 200, download.text
    assert download.content == b"versao inicial"

    updated = api.patch(f"/api/v1/management/documents/{document_id}", headers=headers, json={"description": "Revisto em QA"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["approval_status"] == "pending"

    version = api.post(
        f"/api/v1/management/documents/{document_id}/versions",
        headers=headers,
        json={"file_name": f"relatorio-{suffix}-v2.txt", "file_data_url": _text_data_url("segunda versao"), "change_notes": "Correção QA"},
    )
    assert version.status_code == 200, version.text
    assert version.json()["current_version"] == 2

    rejected = api.post(f"/api/v1/management/documents/{document_id}/review", headers=headers, json={"action": "reject", "notes": "Corrigir metadados"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["approval_status"] == "rejected"

    approved = api.post(f"/api/v1/management/documents/{document_id}/review", headers=headers, json={"action": "approve", "notes": "Aprovado"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"
    api.close()
