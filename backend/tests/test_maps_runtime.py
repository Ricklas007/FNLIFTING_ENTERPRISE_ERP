import sqlite3

import pytest
from fastapi import HTTPException

from app.api.routes.maps import validate_source


def test_validate_mbtiles_extracts_metadata(tmp_path):
    package = tmp_path / "angola.mbtiles"
    with sqlite3.connect(package) as conn:
        conn.execute("create table metadata (name text, value text)")
        conn.execute("create table tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
        conn.executemany(
            "insert into metadata (name, value) values (?, ?)",
            [
                ("format", "png"),
                ("name", "Angola demo raster"),
                ("minzoom", "4"),
                ("maxzoom", "12"),
                ("attribution", "Dados licenciados pelo cliente"),
            ],
        )
        conn.execute("insert into tiles values (4, 8, 8, ?)", (b"tile",))

    provider, metadata = validate_source(package)

    assert provider == "OFFLINE_MBTILES"
    assert metadata["tile_format"] == "png"
    assert metadata["name"] == "Angola demo raster"
    assert metadata["minzoom"] == "4"


def test_validate_rejects_corrupt_pmtiles(tmp_path):
    package = tmp_path / "angola.pmtiles"
    package.write_bytes(b"not-a-pmtiles")

    with pytest.raises(HTTPException) as exc:
        validate_source(package)

    assert exc.value.status_code == 422
