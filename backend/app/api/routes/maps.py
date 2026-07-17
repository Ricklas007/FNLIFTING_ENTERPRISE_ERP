import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import require_permission
from app.core.config import MAP_CACHE_DIR, MAP_DIR
from app.models import User


router = APIRouter(prefix="/maps", tags=["Mapas offline/online"])

PACKAGE_DIR = MAP_DIR / "packages"
MANIFEST_PATH = MAP_DIR / "manifest.json"
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
MAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class MapImportRequest(BaseModel):
    source_path: str = Field(..., min_length=3)
    activate: bool = True
    source: str = "manual"
    license: str = "unknown"
    version: str = "unknown"
    min_zoom: int | None = None
    max_zoom: int | None = None
    bounds: list[float] | None = None


class MapModeRequest(BaseModel):
    mode: Literal["auto", "offline", "online"] = "auto"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"mode": "auto", "active_package_id": None, "packages": []}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.setdefault("mode", "auto")
    manifest.setdefault("active_package_id", None)
    manifest.setdefault("packages", [])
    return manifest


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def package_path(package: dict[str, Any]) -> Path:
    return (PACKAGE_DIR / package["stored_name"]).resolve()


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_source(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Pacote de mapa não encontrado")
    suffix = path.suffix.lower()
    if suffix not in {".pmtiles", ".mbtiles"}:
        raise HTTPException(status_code=422, detail="Formato suportado: PMTiles ou MBTiles")
    if suffix == ".pmtiles":
        with path.open("rb") as handle:
            if handle.read(7) != b"PMTiles":
                raise HTTPException(status_code=422, detail="PMTiles inválido ou corrompido")
        return "OFFLINE_PMTILES", {"tile_format": "pmtiles"}
    metadata: dict[str, Any] = {}
    try:
        with sqlite3.connect(path) as conn:
            tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
            if "tiles" not in tables:
                raise HTTPException(status_code=422, detail="MBTiles sem tabela tiles")
            metadata = dict(conn.execute("select name, value from metadata").fetchall()) if "metadata" in tables else {}
            if metadata.get("format") not in {None, "pbf", "mvt", "png", "jpg", "jpeg", "webp"}:
                raise HTTPException(status_code=422, detail="Formato MBTiles não suportado")
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=422, detail="MBTiles inválido ou corrompido") from exc
    return "OFFLINE_MBTILES", {
        "tile_format": metadata.get("format", "unknown"),
        "name": metadata.get("name"),
        "description": metadata.get("description"),
        "attribution": metadata.get("attribution"),
        "bounds": metadata.get("bounds"),
        "minzoom": metadata.get("minzoom"),
        "maxzoom": metadata.get("maxzoom"),
    }


def provider_status() -> dict[str, Any]:
    manifest = read_manifest()
    active = next((item for item in manifest["packages"] if item["id"] == manifest.get("active_package_id")), None)
    usage = shutil.disk_usage(MAP_DIR)
    return {
        "mode": manifest.get("mode", "auto"),
        "providers": {
            "OFFLINE_PMTILES": {"available": any(item["provider"] == "OFFLINE_PMTILES" for item in manifest["packages"])},
            "OFFLINE_MBTILES": {"available": any(item["provider"] == "OFFLINE_MBTILES" for item in manifest["packages"])},
            "ONLINE_VECTOR": {"available": False, "reason": "Defina provider vectorial online nas configurações."},
            "ONLINE_RASTER": {
                "available": True,
                "style": "osm_raster",
                "attribution": "© OpenStreetMap contributors",
            },
            "MAP_UNAVAILABLE": {"available": active is None},
        },
        "active_package": active,
        "packages": manifest["packages"],
        "storage": {
            "map_dir": str(MAP_DIR),
            "cache_dir": str(MAP_CACHE_DIR),
            "free_bytes": usage.free,
            "total_bytes": usage.total,
        },
        "angola_view": {
            "center": [17.8739, -11.2027],
            "bounds": [11.45, -18.1, 24.1, -4.3],
            "min_zoom": 4,
            "max_zoom": 14,
        },
    }


@router.get("/status")
def maps_status(user: User = Depends(require_permission("fleet.view"))):
    return provider_status()


@router.post("/mode")
def set_map_mode(payload: MapModeRequest, user: User = Depends(require_permission("fleet.manage"))):
    manifest = read_manifest()
    manifest["mode"] = payload.mode
    write_manifest(manifest)
    return provider_status()


@router.post("/packages/import", status_code=status.HTTP_201_CREATED)
def import_package(payload: MapImportRequest, user: User = Depends(require_permission("fleet.manage"))):
    source = Path(payload.source_path).expanduser().resolve()
    provider, metadata = validate_source(source)
    digest = checksum(source)
    package_id = digest[:16]
    stored_name = f"{package_id}{source.suffix.lower()}"
    target = PACKAGE_DIR / stored_name
    if not target.exists():
        shutil.copy2(source, target)
    manifest = read_manifest()
    packages = [item for item in manifest["packages"] if item["id"] != package_id]
    record = {
        "id": package_id,
        "provider": provider,
        "original_name": source.name,
        "stored_name": stored_name,
        "size_bytes": target.stat().st_size,
        "checksum_sha256": digest,
        "source": payload.source,
        "license": payload.license,
        "version": payload.version,
        "bounds": payload.bounds,
        "min_zoom": payload.min_zoom or _safe_int(metadata.get("minzoom")),
        "max_zoom": payload.max_zoom or _safe_int(metadata.get("maxzoom")),
        "tile_format": metadata.get("tile_format"),
        "metadata": metadata,
        "imported_at": now_iso(),
        "imported_by": user.id,
    }
    packages.append(record)
    manifest["packages"] = packages
    if payload.activate:
        manifest["active_package_id"] = package_id
    write_manifest(manifest)
    return record


@router.post("/packages/{package_id}/activate")
def activate_package(package_id: str, user: User = Depends(require_permission("fleet.manage"))):
    manifest = read_manifest()
    if not any(item["id"] == package_id for item in manifest["packages"]):
        raise HTTPException(status_code=404, detail="Pacote de mapa não encontrado")
    manifest["active_package_id"] = package_id
    write_manifest(manifest)
    return {"message": "Pacote de mapa ativado", "package_id": package_id}


@router.post("/packages/deactivate")
def deactivate_package(user: User = Depends(require_permission("fleet.manage"))):
    manifest = read_manifest()
    manifest["active_package_id"] = None
    write_manifest(manifest)
    return {"message": "Mapa offline desativado"}


@router.delete("/packages/{package_id}")
def remove_package(package_id: str, user: User = Depends(require_permission("fleet.manage"))):
    manifest = read_manifest()
    record = next((item for item in manifest["packages"] if item["id"] == package_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Pacote de mapa não encontrado")
    path = package_path(record)
    if path.exists():
        path.unlink()
    manifest["packages"] = [item for item in manifest["packages"] if item["id"] != package_id]
    if manifest.get("active_package_id") == package_id:
        manifest["active_package_id"] = None
    write_manifest(manifest)
    return {"message": "Pacote removido"}


@router.get("/packages/{package_id}/pmtiles")
def get_pmtiles(package_id: str):
    manifest = read_manifest()
    record = next((item for item in manifest["packages"] if item["id"] == package_id), None)
    if not record or record["provider"] != "OFFLINE_PMTILES":
        raise HTTPException(status_code=404, detail="PMTiles não encontrado")
    return FileResponse(package_path(record), media_type="application/octet-stream")


@router.get("/packages/{package_id}/tiles/{z}/{x}/{y}.{extension}")
def get_mbtiles_tile(package_id: str, z: int, x: int, y: int, extension: str):
    manifest = read_manifest()
    record = next((item for item in manifest["packages"] if item["id"] == package_id), None)
    if not record or record["provider"] != "OFFLINE_MBTILES":
        raise HTTPException(status_code=404, detail="MBTiles não encontrado")
    path = package_path(record)
    tms_y = (1 << z) - 1 - y
    with sqlite3.connect(path) as conn:
        tables = {table[0] for table in conn.execute("select name from sqlite_master where type='table'")}
        row = conn.execute(
            "select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?",
            (z, x, tms_y),
        ).fetchone()
        metadata = dict(conn.execute("select name, value from metadata").fetchall()) if "metadata" in tables else {}
    if not row:
        raise HTTPException(status_code=404, detail="Tile não encontrado")
    fmt = metadata.get("format", extension).lower()
    media = {
        "pbf": "application/x-protobuf",
        "mvt": "application/x-protobuf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(fmt, "application/octet-stream")
    return Response(content=row[0], media_type=media, headers={"Cache-Control": "public, max-age=86400"})
