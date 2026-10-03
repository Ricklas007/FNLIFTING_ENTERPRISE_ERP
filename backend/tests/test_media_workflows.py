import base64

from tests.enterprise_test_utils import (
    client,
    first_asset_id,
    first_employee_id,
    first_equipment_id,
    first_truck_id,
    login_headers,
)


PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2&\xbb\x00\x00\x00\x00IEND\xaeB`\x82"
).decode("ascii")


def _upload_and_verify(api, headers, entity_type: str, entity_id: str):
    created = api.post(
        f"/api/v1/management/media/entities/{entity_type}/{entity_id}",
        headers=headers,
        json={
            "title": f"QA {entity_type}",
            "category": "photo",
            "caption": "Imagem de validação automatizada",
            "file_name": f"{entity_type}.png",
            "file_data_url": PNG_DATA_URL,
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["thumbnail_available"] is True
    assert payload["checksum_sha256"]

    listed = api.get(f"/api/v1/management/media/entities/{entity_type}/{entity_id}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == payload["id"] for item in listed.json())

    download = api.get(f"/api/v1/management/media/{payload['id']}/download", headers=headers)
    assert download.status_code == 200, download.text
    assert download.headers["content-type"].startswith("image/png")

    thumbnail = api.get(f"/api/v1/management/media/{payload['id']}/thumbnail", headers=headers)
    assert thumbnail.status_code == 200, thumbnail.text
    return payload["id"]


def test_media_upload_preview_download_archive_for_core_entities():
    api = client()
    headers = login_headers(api)
    targets = [
        ("employee", first_employee_id()),
        ("equipment", first_equipment_id()),
        ("truck", first_truck_id()),
        ("asset", first_asset_id()),
    ]
    created_ids = [_upload_and_verify(api, headers, entity_type, entity_id) for entity_type, entity_id in targets]
    archived = api.delete(f"/api/v1/management/media/{created_ids[0]}", headers=headers)
    assert archived.status_code == 200, archived.text
    missing = api.get(f"/api/v1/management/media/{created_ids[0]}/download", headers=headers)
    assert missing.status_code == 404
    api.close()
