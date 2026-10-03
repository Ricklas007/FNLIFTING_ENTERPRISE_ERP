import sqlite3
from uuid import uuid4

from tests.enterprise_test_utils import client, login_headers


PNG_TILE = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff"
    b"\xff?\x00\x05\xfe\x02\xfeA\xe2&\xbb\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_real_angola_mbtiles_package_import_validate_activate_and_tile_serving(tmp_path):
    api = client()
    headers = login_headers(api)
    path = tmp_path / f"angola-{uuid4().hex[:8]}.mbtiles"
    with sqlite3.connect(path) as conn:
        conn.execute("create table metadata (name text, value text)")
        conn.execute("create table tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
        conn.executemany(
            "insert into metadata (name, value) values (?, ?)",
            [
                ("name", "Angola QA Offline"),
                ("description", "Pacote QA com bounds oficiais de Angola para validação de runtime"),
                ("format", "png"),
                ("bounds", "11.66,-18.04,24.09,-4.38"),
                ("minzoom", "0"),
                ("maxzoom", "1"),
                ("attribution", "OpenStreetMap contributors / QA local"),
            ],
        )
        conn.execute("insert into tiles values (0, 0, 0, ?)", (PNG_TILE,))

    imported = api.post(
        "/api/v1/maps/packages/import",
        headers=headers,
        json={
            "source_path": str(path),
            "activate": True,
            "source": "OSM local QA",
            "license": "ODbL",
            "version": "2026-QA",
            "min_zoom": 0,
            "max_zoom": 1,
            "bounds": [11.66, -18.04, 24.09, -4.38],
        },
    )
    assert imported.status_code == 201, imported.text
    payload = imported.json()
    assert payload["provider"] == "OFFLINE_MBTILES"
    assert payload["active"] is True
    assert payload["latest_validation"]["status"] == "valid"

    validated = api.post(f"/api/v1/maps/packages/{payload['id']}/validate", headers=headers)
    assert validated.status_code == 200, validated.text
    activated = api.post(f"/api/v1/maps/packages/{payload['id']}/activate", headers=headers)
    assert activated.status_code == 200, activated.text
    tile = api.get(f"/api/v1/maps/packages/{payload['id']}/tiles/0/0/0.png", headers=headers)
    assert tile.status_code == 200, tile.text
    assert tile.headers["content-type"].startswith("image/png")
    api.close()
