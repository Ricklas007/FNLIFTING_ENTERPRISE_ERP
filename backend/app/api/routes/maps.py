import hashlib
import json
import logging
import mimetypes
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import MAP_CACHE_DIR, MAP_DIR
from app.database.session import get_db
from app.models import AuditLog, MapPackage, MapPackageActivation, MapPackageUsage, MapPackageValidation, User
from app.models.common import utcnow


router = APIRouter(prefix="/maps", tags=["Mapas offline/online"])
logger = logging.getLogger(__name__)

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


class MapPlaceResult(BaseModel):
    external_id: str
    title: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    latitude: float
    longitude: float
    rating: float | None = None
    reviews: int | None = None
    hours: str | None = None
    thumbnail: str | None = None
    source: str = "SERPAPI_GOOGLE_MAPS"
    retrieved_at: str


class SerpApiStatus(BaseModel):
    provider: str = "SERPAPI_GOOGLE_MAPS"
    status: str
    configured: bool
    enabled: bool
    base_url: str | None = None
    message: str
    checked_at: datetime
    cache_ttl_seconds: int
    rate_limit_per_minute: int
    last_success_at: str | None = None
    last_error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class SerpApiProviderError(Exception):
    def __init__(self, status_value: str, http_status: int, message: str):
        self.status_value = status_value
        self.http_status = http_status
        self.message = message
        super().__init__(message)


_SERPAPI_CALLS: dict[str, list[float]] = {}
_SERPAPI_CACHE: dict[str, tuple[float, list[MapPlaceResult]]] = {}
_SERPAPI_METRICS: dict[str, Any] = {
    "requests": 0,
    "successes": 0,
    "errors": 0,
    "cache_hits": 0,
    "last_status": None,
    "last_checked_at": None,
    "last_success_at": None,
    "last_error": None,
}


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


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _safe_positive_int_env(*names: str, default: int) -> int:
    for name in names:
        raw = os.getenv(name)
        if raw in (None, ""):
            continue
        try:
            value = int(raw)
        except ValueError:
            continue
        if value > 0:
            return value
    return default


def _safe_positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _serpapi_rate_limit() -> int:
    return _safe_positive_int_env("SERPAPI_RATE_LIMIT_PER_MINUTE", "SERPAPI_RATE_LIMIT", default=20)


def _serpapi_cache_ttl() -> int:
    return _safe_positive_int_env("SERPAPI_CACHE_TTL", default=300)


def _serpapi_base_url() -> str:
    return (os.getenv("SERPAPI_BASE_URL") or "https://serpapi.com/search").strip()


def _serpapi_config() -> tuple[bool, bool, str, str, float]:
    enabled = _truthy(os.getenv("SERPAPI_ENABLED"))
    key = (os.getenv("SERPAPI_KEY") or "").strip()
    base_url = _serpapi_base_url()
    timeout = _safe_positive_float_env("SERPAPI_TIMEOUT", 8.0)
    return enabled, bool(key), key, base_url, timeout


def _serpapi_enabled() -> bool:
    enabled, has_key, *_ = _serpapi_config()
    return enabled and has_key


def _check_serpapi_rate(user_id: str) -> None:
    window_seconds = 60
    limit = _serpapi_rate_limit()
    now = time.time()
    calls = [item for item in _SERPAPI_CALLS.get(user_id, []) if now - item < window_seconds]
    if len(calls) >= limit:
        raise HTTPException(status_code=429, detail="Limite de pesquisa de locais atingido. Tente novamente dentro de instantes.")
    calls.append(now)
    _SERPAPI_CALLS[user_id] = calls


def _redact_provider_message(message: str) -> str:
    key = (os.getenv("SERPAPI_KEY") or "").strip()
    result = str(message or "").strip()
    if key:
        result = result.replace(key, "***")
    return result[:240]


def _classify_serpapi_error(message: str, http_code: int | None = None) -> tuple[str, int, str]:
    text = str(message or "").lower()
    if http_code in {401, 403} or any(part in text for part in ("invalid api key", "api key is invalid", "unauthorized", "forbidden")):
        return "AUTH_ERROR", 502, "SerpApi recusou a chave configurada."
    if http_code == 429 or any(part in text for part in ("quota", "credits", "credit", "plan limit", "exceeded")):
        return "QUOTA_EXCEEDED", 429, "Quota SerpApi atingida."
    if "rate" in text:
        return "RATE_LIMITED", 429, "Limite de frequência SerpApi atingido."
    return "PROVIDER_ERROR", 502, f"SerpApi: {_redact_provider_message(message) or 'erro do fornecedor.'}"


def _remember_serpapi(status_value: str, error: str | None = None) -> None:
    timestamp = now_iso()
    _SERPAPI_METRICS["last_status"] = status_value
    _SERPAPI_METRICS["last_checked_at"] = timestamp
    if status_value == "CONNECTED":
        _SERPAPI_METRICS["successes"] += 1
        _SERPAPI_METRICS["last_success_at"] = timestamp
        _SERPAPI_METRICS["last_error"] = None
    else:
        _SERPAPI_METRICS["errors"] += 1
        _SERPAPI_METRICS["last_error"] = _redact_provider_message(error or status_value)


def _serpapi_cache_key(params: dict[str, Any]) -> str:
    safe_params = {key: value for key, value in params.items() if key != "api_key"}
    return json.dumps(sorted(safe_params.items()), ensure_ascii=False, default=str)


def _make_serpapi_params(
    query: str,
    latitude: float | None,
    longitude: float | None,
    zoom: int,
    language: str,
    country: str,
    category: str | None,
    limit: int,
    page: int,
) -> dict[str, Any]:
    _, _, key, _, _ = _serpapi_config()
    params: dict[str, Any] = {
        "engine": "google_maps",
        "q": f"{query} {category or ''}".strip(),
        "hl": language,
        "gl": country.lower(),
        "api_key": key,
    }
    if latitude is not None and longitude is not None:
        params["ll"] = f"@{latitude},{longitude},{zoom}z"
    else:
        params["location"] = "Angola"
    if page > 1:
        params["start"] = (page - 1) * limit
    return params


def _fetch_serpapi_places(params: dict[str, Any], limit: int, *, use_cache: bool = True) -> tuple[list[MapPlaceResult], bool]:
    if not _serpapi_enabled():
        raise SerpApiProviderError("NOT_CONFIGURED", 503, "SerpApi não configurada. Defina SERPAPI_ENABLED=true e SERPAPI_KEY apenas no backend.")
    cache_key = _serpapi_cache_key(params)
    ttl = _serpapi_cache_ttl()
    now = time.time()
    if use_cache and ttl > 0:
        cached = _SERPAPI_CACHE.get(cache_key)
        if cached and cached[0] > now:
            _SERPAPI_METRICS["cache_hits"] += 1
            return cached[1][:limit], True
    _SERPAPI_METRICS["requests"] += 1
    _, _, _, base_url, timeout = _serpapi_config()
    url = f"{base_url}?{urlencode(params)}"
    request = UrlRequest(url, headers={"Accept": "application/json", "User-Agent": "FNLIFTING-ERP/0.12.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        status_value, http_status, public_message = _classify_serpapi_error(str(exc.reason or exc), exc.code)
        _remember_serpapi(status_value, public_message)
        logger.warning("SerpApi place search failed", extra={"serpapi_status": status_value, "http_status": exc.code})
        raise SerpApiProviderError(status_value, http_status, public_message) from exc
    except TimeoutError as exc:
        _remember_serpapi("TIMEOUT", "Timeout ao pesquisar locais na SerpApi.")
        logger.warning("SerpApi place search timed out", extra={"serpapi_status": "TIMEOUT"})
        raise SerpApiProviderError("TIMEOUT", 504, "Timeout ao pesquisar locais na SerpApi.") from exc
    except URLError as exc:
        reason = _redact_provider_message(str(exc.reason or exc))
        _remember_serpapi("PROVIDER_ERROR", reason)
        logger.warning("SerpApi network error", extra={"serpapi_status": "PROVIDER_ERROR"})
        raise SerpApiProviderError("PROVIDER_ERROR", 502, f"SerpApi indisponível: {reason}") from exc
    except json.JSONDecodeError as exc:
        _remember_serpapi("PROVIDER_ERROR", "Resposta SerpApi inválida.")
        logger.warning("SerpApi invalid JSON", extra={"serpapi_status": "PROVIDER_ERROR"})
        raise SerpApiProviderError("PROVIDER_ERROR", 502, "Resposta SerpApi inválida.") from exc
    if payload.get("error"):
        status_value, http_status, public_message = _classify_serpapi_error(str(payload["error"]))
        _remember_serpapi(status_value, public_message)
        logger.warning("SerpApi payload error", extra={"serpapi_status": status_value})
        raise SerpApiProviderError(status_value, http_status, public_message)
    local_results = payload.get("local_results") or payload.get("place_results") or []
    if isinstance(local_results, dict):
        local_results = [local_results]
    retrieved_at = now_iso()
    seen: set[str] = set()
    normalized: list[MapPlaceResult] = []
    for item in local_results:
        if not isinstance(item, dict):
            continue
        place = _normalize_serpapi_place(item, retrieved_at)
        if not place:
            continue
        dedupe_key = f"{place.external_id}|{round(place.latitude, 6)}|{round(place.longitude, 6)}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(place)
    result = normalized[:limit]
    if ttl > 0:
        _SERPAPI_CACHE[cache_key] = (now + ttl, result)
    _remember_serpapi("CONNECTED")
    return result, False


def serpapi_status_snapshot() -> SerpApiStatus:
    enabled, has_key, _, base_url, _ = _serpapi_config()
    if not enabled or not has_key:
        status_value = "NOT_CONFIGURED"
        message = "SerpApi não configurada no backend."
    else:
        status_value = str(_SERPAPI_METRICS.get("last_status") or "DEGRADED")
        message = "Configurada; execute o teste para validar a ligação." if status_value == "DEGRADED" else "Último estado conhecido da SerpApi."
    return SerpApiStatus(
        status=status_value,
        configured=has_key,
        enabled=enabled,
        base_url=base_url if has_key else None,
        message=message,
        checked_at=datetime.now(timezone.utc),
        cache_ttl_seconds=_serpapi_cache_ttl(),
        rate_limit_per_minute=_serpapi_rate_limit(),
        last_success_at=_SERPAPI_METRICS.get("last_success_at"),
        last_error=_SERPAPI_METRICS.get("last_error"),
        metrics={
            "requests": _SERPAPI_METRICS["requests"],
            "successes": _SERPAPI_METRICS["successes"],
            "errors": _SERPAPI_METRICS["errors"],
            "cache_hits": _SERPAPI_METRICS["cache_hits"],
            "last_checked_at": _SERPAPI_METRICS.get("last_checked_at"),
        },
    )


def serpapi_health_check(query: str = "Luanda") -> SerpApiStatus:
    enabled, has_key, _, base_url, _ = _serpapi_config()
    checked_at = datetime.now(timezone.utc)
    if not enabled or not has_key:
        return SerpApiStatus(
            status="NOT_CONFIGURED",
            configured=has_key,
            enabled=enabled,
            base_url=None,
            message="SerpApi não configurada no backend.",
            checked_at=checked_at,
            cache_ttl_seconds=_serpapi_cache_ttl(),
            rate_limit_per_minute=_serpapi_rate_limit(),
            last_success_at=_SERPAPI_METRICS.get("last_success_at"),
            last_error=_SERPAPI_METRICS.get("last_error"),
            metrics=dict(_SERPAPI_METRICS),
        )
    params = _make_serpapi_params(query, -8.839, 13.289, 10, "pt", "ao", None, 3, 1)
    try:
        results, cache_hit = _fetch_serpapi_places(params, 3, use_cache=False)
        message = f"Ligação SerpApi validada com {len(results)} resultado(s)."
        status_value = "CONNECTED"
        last_error = None
    except SerpApiProviderError as exc:
        status_value = exc.status_value
        message = exc.message
        cache_hit = False
        last_error = exc.message
    metrics = {
        "requests": _SERPAPI_METRICS["requests"],
        "successes": _SERPAPI_METRICS["successes"],
        "errors": _SERPAPI_METRICS["errors"],
        "cache_hits": _SERPAPI_METRICS["cache_hits"],
        "test_cache_hit": cache_hit,
    }
    return SerpApiStatus(
        status=status_value,
        configured=True,
        enabled=True,
        base_url=base_url,
        message=message,
        checked_at=checked_at,
        cache_ttl_seconds=_serpapi_cache_ttl(),
        rate_limit_per_minute=_serpapi_rate_limit(),
        last_success_at=_SERPAPI_METRICS.get("last_success_at"),
        last_error=last_error or _SERPAPI_METRICS.get("last_error"),
        metrics=metrics,
    )


def audit_serpapi_event(db: Session, request: Request, user: User, action: str, description: str, after: dict[str, Any] | None = None) -> None:
    safe_after = dict(after or {})
    safe_after.pop("api_key", None)
    db.add(AuditLog(
        company_id=user.company_id,
        user_id=user.id,
        action=action,
        entity_type="integration",
        entity_id=None,
        entity_label="SERPAPI_GOOGLE_MAPS",
        after_data=json.dumps(safe_after, ensure_ascii=False, default=str) if safe_after else None,
        ip_address=request.client.host if request.client else None,
        machine_name=(request.headers.get("x-machine-name") or request.headers.get("user-agent") or "")[:160],
        description=description,
        created_by=user.id,
    ))


def _normalize_serpapi_place(item: dict[str, Any], retrieved_at: str) -> MapPlaceResult | None:
    gps = item.get("gps_coordinates") or {}
    lat = gps.get("latitude") or item.get("latitude")
    lon = gps.get("longitude") or item.get("longitude")
    try:
        latitude = float(lat)
        longitude = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    try:
        reviews = int(item["reviews"]) if item.get("reviews") is not None else None
    except (TypeError, ValueError):
        reviews = None
    try:
        rating = float(item["rating"]) if item.get("rating") is not None else None
    except (TypeError, ValueError):
        rating = None
    return MapPlaceResult(
        external_id=str(item.get("place_id") or item.get("data_id") or item.get("cid") or item.get("title") or f"{latitude},{longitude}"),
        title=str(item.get("title") or item.get("name") or "Local sem nome"),
        category=item.get("type") or item.get("category"),
        address=item.get("address"),
        phone=item.get("phone"),
        website=item.get("website"),
        latitude=latitude,
        longitude=longitude,
        rating=rating,
        reviews=reviews,
        hours=item.get("hours"),
        thumbnail=item.get("thumbnail"),
        retrieved_at=retrieved_at,
    )


def package_path(package: dict[str, Any]) -> Path:
    stored_name = str(package.get("stored_name") or "").strip()
    target = (PACKAGE_DIR / stored_name).resolve()
    try:
        target.relative_to(PACKAGE_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Caminho do pacote de mapa inválido") from exc
    return target


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_source(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Pacote de mapa nÃ£o encontrado")
    suffix = path.suffix.lower()
    if suffix not in {".pmtiles", ".mbtiles"}:
        raise HTTPException(status_code=422, detail="Formato suportado: PMTiles ou MBTiles")
    if suffix == ".pmtiles":
        with path.open("rb") as handle:
            if handle.read(7) != b"PMTiles":
                raise HTTPException(status_code=422, detail="PMTiles invÃ¡lido ou corrompido")
        return "OFFLINE_PMTILES", {"tile_format": "pmtiles"}
    metadata: dict[str, Any] = {}
    conn = None
    try:
        conn = sqlite3.connect(path)
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
        if "tiles" not in tables:
            raise HTTPException(status_code=422, detail="MBTiles sem tabela tiles")
        metadata = dict(conn.execute("select name, value from metadata").fetchall()) if "metadata" in tables else {}
        if metadata.get("format") not in {None, "pbf", "mvt", "png", "jpg", "jpeg", "webp"}:
            raise HTTPException(status_code=422, detail="Formato MBTiles nÃ£o suportado")
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=422, detail="MBTiles invÃ¡lido ou corrompido") from exc
    finally:
        if conn is not None:
            conn.close()
    return "OFFLINE_MBTILES", {
        "tile_format": metadata.get("format", "unknown"),
        "name": metadata.get("name"),
        "description": metadata.get("description"),
        "attribution": metadata.get("attribution"),
        "bounds": metadata.get("bounds"),
        "minzoom": metadata.get("minzoom"),
        "maxzoom": metadata.get("maxzoom"),
    }


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _normalize_bounds(value: Any) -> list[float] | None:
    if value in (None, "", []):
        return None
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise HTTPException(status_code=422, detail="Bounds do mapa devem conter oeste, sul, este e norte")
    try:
        west, south, east, north = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Bounds do mapa contêm valores inválidos") from exc
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90 and west < east and south < north):
        raise HTTPException(status_code=422, detail="Bounds do mapa estão fora de intervalo")
    return [west, south, east, north]


def _map_package_max_bytes() -> int:
    return _safe_positive_int_env("MAP_PACKAGE_MAX_BYTES", default=5 * 1024 * 1024 * 1024)


def _package_record_path(record: MapPackage) -> Path:
    return package_path({"stored_name": record.stored_name})


def _package_manifest_record(record: MapPackage) -> dict[str, Any]:
    metadata = _json_loads(record.metadata_json, {})
    return {
        "id": record.id,
        "company_id": record.company_id,
        "provider": record.provider,
        "original_name": record.original_name,
        "stored_name": record.stored_name,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "checksum_sha256": record.checksum_sha256,
        "source": record.source,
        "license": record.license,
        "version": record.version,
        "bounds": _json_loads(record.bounds_json, None),
        "min_zoom": record.min_zoom,
        "max_zoom": record.max_zoom,
        "tile_format": metadata.get("tile_format"),
        "metadata": metadata,
        "status": record.status,
        "active": record.active,
        "imported_at": record.imported_at.isoformat() if record.imported_at else None,
        "imported_by": record.created_by,
    }


def _map_package_out(record: MapPackage, latest_validation: MapPackageValidation | None = None) -> dict[str, Any]:
    payload = _package_manifest_record(record)
    payload["latest_validation"] = None
    if latest_validation:
        payload["latest_validation"] = {
            "id": latest_validation.id,
            "status": latest_validation.status,
            "checks": _json_loads(latest_validation.checks_json, {}),
            "errors": _json_loads(latest_validation.errors_json, []),
            "validated_at": latest_validation.validated_at.isoformat() if latest_validation.validated_at else None,
        }
    return payload


def _latest_package_validation(db: Session, package_id: str) -> MapPackageValidation | None:
    return db.scalars(
        select(MapPackageValidation)
        .where(MapPackageValidation.package_id == package_id)
        .order_by(MapPackageValidation.validated_at.desc(), MapPackageValidation.created_at.desc())
    ).first()


def _tenant_package(db: Session, user: User, package_id: str) -> MapPackage:
    record = db.scalar(
        select(MapPackage).where(
            MapPackage.id == package_id,
            MapPackage.company_id == user.company_id,
            MapPackage.deleted_at.is_(None),
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="Pacote de mapa não encontrado")
    return record


def _tenant_packages(db: Session, user: User) -> list[MapPackage]:
    return list(
        db.scalars(
            select(MapPackage)
            .where(MapPackage.company_id == user.company_id, MapPackage.deleted_at.is_(None))
            .order_by(MapPackage.imported_at.desc(), MapPackage.created_at.desc())
        )
    )


def _sync_manifest_record(record: MapPackage) -> None:
    manifest = read_manifest()
    packages = [item for item in manifest["packages"] if item.get("id") != record.id]
    if record.deleted_at is None and record.status != "deleted":
        packages.append(_package_manifest_record(record))
    manifest["packages"] = packages
    if record.active and record.deleted_at is None:
        manifest["active_package_id"] = record.id
    elif manifest.get("active_package_id") == record.id:
        manifest["active_package_id"] = None
    write_manifest(manifest)


def _sync_manifest_activation(package_id: str | None) -> None:
    manifest = read_manifest()
    manifest["active_package_id"] = package_id
    for item in manifest["packages"]:
        item["active"] = item.get("id") == package_id
    write_manifest(manifest)


def _validate_package_file(path: Path, payload: MapImportRequest | None = None, *, company_id: str | None = None) -> dict[str, Any]:
    provider, metadata = validate_source(path)
    size_bytes = path.stat().st_size
    digest = checksum(path)
    guessed_mime = mimetypes.guess_type(path.name)[0]
    suffix = path.suffix.lower()
    allowed_mime = {
        ".pmtiles": {None, "application/octet-stream", "application/vnd.pmtiles", "application/x-pmtiles"},
        ".mbtiles": {None, "application/octet-stream", "application/x-sqlite3", "application/vnd.sqlite3", "application/geopackage+sqlite3"},
    }
    min_zoom = payload.min_zoom if payload and payload.min_zoom is not None else _safe_int(metadata.get("minzoom"))
    max_zoom = payload.max_zoom if payload and payload.max_zoom is not None else _safe_int(metadata.get("maxzoom"))
    bounds_source = payload.bounds if payload and payload.bounds is not None else metadata.get("bounds")
    bounds = _normalize_bounds(bounds_source)
    license_value = (payload.license if payload else None) or metadata.get("license") or "unknown"
    checks: dict[str, Any] = {
        "extension": {"status": "pass", "value": suffix},
        "mime": {"status": "pass" if guessed_mime in allowed_mime.get(suffix, {None}) else "warning", "value": guessed_mime or "unknown"},
        "signature": {"status": "pass", "provider": provider},
        "checksum": {"status": "pass", "sha256": digest},
        "size": {"status": "pass", "bytes": size_bytes, "max_bytes": _map_package_max_bytes()},
        "path_traversal": {"status": "pass", "resolved": str(path)},
        "free_space": {"status": "pass", "free_bytes": shutil.disk_usage(PACKAGE_DIR).free},
        "tenant": {"status": "pass", "company_id": company_id},
        "bounds": {"status": "pass" if bounds else "warning", "value": bounds},
        "zoom": {"status": "pass" if min_zoom is not None and max_zoom is not None else "warning", "min_zoom": min_zoom, "max_zoom": max_zoom},
        "license": {"status": "pass" if str(license_value).strip().lower() not in {"", "unknown", "none"} else "warning", "value": license_value},
    }
    errors: list[str] = []
    if size_bytes <= 0:
        errors.append("O pacote está vazio.")
        checks["size"]["status"] = "fail"
    if size_bytes > _map_package_max_bytes():
        errors.append("O pacote excede o tamanho máximo permitido.")
        checks["size"]["status"] = "fail"
    if shutil.disk_usage(PACKAGE_DIR).free < size_bytes + (10 * 1024 * 1024):
        errors.append("Espaço livre insuficiente para importar o mapa.")
        checks["free_space"]["status"] = "fail"
    if min_zoom is not None and max_zoom is not None and min_zoom > max_zoom:
        errors.append("Zoom mínimo não pode ser superior ao zoom máximo.")
        checks["zoom"]["status"] = "fail"
    if guessed_mime not in allowed_mime.get(suffix, {None}):
        checks["mime"]["message"] = "MIME inferido não é típico para o formato; assinatura interna foi validada."
    return {
        "provider": provider,
        "metadata": metadata,
        "checksum_sha256": digest,
        "mime_type": guessed_mime,
        "size_bytes": size_bytes,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "bounds": bounds,
        "license": license_value,
        "checks": checks,
        "errors": errors,
    }


def _record_package_validation(db: Session, user: User, record: MapPackage, validation: dict[str, Any]) -> MapPackageValidation:
    status_value = "valid" if not validation["errors"] else "failed"
    row = MapPackageValidation(
        company_id=user.company_id,
        package_id=record.id,
        status=status_value,
        checks_json=_json_dumps(validation["checks"]),
        errors_json=_json_dumps(validation["errors"]) if validation["errors"] else None,
        validated_at=utcnow(),
        created_by=user.id,
    )
    record.status = "validated" if status_value == "valid" else "invalid"
    record.updated_by = user.id
    db.add(row)
    return row


def _record_package_usage(db: Session, user: User, record: MapPackage, usage_type: str, endpoint: str, bytes_served: int) -> None:
    db.add(MapPackageUsage(
        company_id=user.company_id,
        package_id=record.id,
        usage_type=usage_type,
        endpoint=endpoint[:160],
        bytes_served=max(bytes_served, 0),
        created_by=user.id,
    ))


def _activate_package_record(db: Session, user: User, record: MapPackage, reason: str) -> None:
    latest_validation = _latest_package_validation(db, record.id)
    if latest_validation and latest_validation.status != "valid":
        raise HTTPException(status_code=422, detail="Pacote de mapa inválido; valide o ficheiro antes de ativar")
    previous = db.scalar(
        select(MapPackage).where(
            MapPackage.company_id == user.company_id,
            MapPackage.active.is_(True),
            MapPackage.deleted_at.is_(None),
        )
    )
    record.active = True
    record.status = "active"
    record.updated_by = user.id
    for item in _tenant_packages(db, user):
        item.active = item.id == record.id
        if item.id == record.id:
            item.status = "active"
        elif item.status == "active":
            item.status = "validated"
        item.updated_by = user.id
    db.add(MapPackageActivation(
        company_id=user.company_id,
        package_id=record.id,
        previous_package_id=previous.id if previous and previous.id != record.id else None,
        action="activate",
        reason=reason,
        created_by=user.id,
    ))
    _sync_manifest_activation(record.id)


def _deactivate_package_record(db: Session, user: User, record: MapPackage | None, reason: str) -> None:
    package_id = record.id if record else None
    for item in _tenant_packages(db, user):
        if record is None or item.id == record.id:
            item.active = False
            if item.status == "active":
                item.status = "validated"
            item.updated_by = user.id
    if package_id:
        db.add(MapPackageActivation(
            company_id=user.company_id,
            package_id=package_id,
            previous_package_id=package_id,
            action="deactivate",
            reason=reason,
            created_by=user.id,
        ))
    _sync_manifest_activation(None)


def provider_status(db: Session | None = None, user: User | None = None) -> dict[str, Any]:
    manifest = read_manifest()
    mode = manifest.get("mode", "auto")
    package_rows = _tenant_packages(db, user) if db is not None and user is not None else []
    packages = [_map_package_out(item, _latest_package_validation(db, item.id) if db is not None else None) for item in package_rows]
    if packages:
        active = next((item for item in packages if item.get("active")), None)
    else:
        packages = manifest["packages"]
        active = next((item for item in packages if item["id"] == manifest.get("active_package_id")), None)
    usage = shutil.disk_usage(MAP_DIR)
    serpapi = serpapi_status_snapshot()
    google_configured = bool(os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("VITE_GOOGLE_MAPS_API_KEY"))
    if mode == "offline" and active:
        active_provider = active["provider"]
    elif mode == "auto" and active:
        active_provider = active["provider"]
    else:
        active_provider = "ONLINE_RASTER"
    return {
        "mode": mode,
        "default_provider": os.getenv("MAP_DEFAULT_PROVIDER", "ONLINE_RASTER"),
        "active_provider": active_provider,
        "offline_active": bool(active and mode in {"auto", "offline"}),
        "providers": {
            "OFFLINE_PMTILES": {"available": any(item["provider"] == "OFFLINE_PMTILES" for item in packages)},
            "OFFLINE_MBTILES": {"available": any(item["provider"] == "OFFLINE_MBTILES" for item in packages)},
            "ONLINE_VECTOR": {"available": False, "reason": "Defina provider vectorial online nas configuraÃ§Ãµes."},
            "ONLINE_RASTER": {
                "available": True,
                "status": "CONNECTED",
                "style": "carto_dark_raster",
                "attribution": "© OpenStreetMap contributors © CARTO",
            },
            "GOOGLE_ONLINE": {
                "available": google_configured,
                "configured": google_configured,
                "status": "CONFIGURED" if google_configured else "NOT_CONFIGURED",
                "reason": "Requer Google Maps JavaScript API key oficial com restrições e billing ativo.",
            },
            "SERPAPI_PLACE_SEARCH": {
                "available": serpapi.enabled and serpapi.configured,
                "role": "AUXILIARY_PLACE_SEARCH",
                "status": serpapi.status,
                "message": serpapi.message,
                "last_success_at": serpapi.last_success_at,
                "last_error": serpapi.last_error,
                "rate_limit_per_minute": serpapi.rate_limit_per_minute,
                "cache_ttl_seconds": serpapi.cache_ttl_seconds,
                "metrics": serpapi.metrics,
            },
            "MAP_UNAVAILABLE": {"available": active is None},
        },
        "active_package": active,
        "packages": packages,
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
def maps_status(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return provider_status(db, user)


@router.post("/mode")
def set_map_mode(payload: MapModeRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    manifest = read_manifest()
    manifest["mode"] = payload.mode
    write_manifest(manifest)
    return provider_status(db, user)


@router.get("/places/search", response_model=list[MapPlaceResult])
def search_places(
    request: Request,
    query: str = Query(..., min_length=2, max_length=160),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    zoom: int = Query(default=10, ge=3, le=20),
    language: str = Query(default="pt", min_length=2, max_length=8),
    country: str = Query(default="ao", min_length=2, max_length=6),
    category: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=8, ge=1, le=20),
    page: int = Query(default=1, ge=1, le=10),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    if not _serpapi_enabled():
        raise HTTPException(status_code=503, detail="SerpApi não configurada. Defina SERPAPI_ENABLED=true e SERPAPI_KEY apenas no backend.")
    try:
        _check_serpapi_rate(user.id)
    except HTTPException as exc:
        _remember_serpapi("RATE_LIMITED", str(exc.detail))
        audit_serpapi_event(db, request, user, "rate_limited", "Pesquisa SerpApi bloqueada por rate limit local", {"query": query, "status": "RATE_LIMITED"})
        db.commit()
        raise
    params = _make_serpapi_params(query, latitude, longitude, zoom, language, country, category, limit, page)
    try:
        results, cache_hit = _fetch_serpapi_places(params, limit)
    except SerpApiProviderError as exc:
        audit_serpapi_event(db, request, user, "provider_error", "Pesquisa SerpApi falhou", {"query": query, "status": exc.status_value})
        db.commit()
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
    audit_serpapi_event(db, request, user, "search", "Pesquisa SerpApi executada", {
        "query": query,
        "category": category,
        "country": country,
        "page": page,
        "limit": limit,
        "result_count": len(results),
        "cache_hit": cache_hit,
        "status": "CONNECTED",
    })
    db.commit()
    return results


@router.get("/packages")
def list_packages(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    rows = _tenant_packages(db, user)
    if rows:
        return [_map_package_out(item, _latest_package_validation(db, item.id)) for item in rows]
    manifest = read_manifest()
    return [
        item for item in manifest["packages"]
        if item.get("company_id") in (None, user.company_id)
    ]


@router.get("/packages/active")
def get_active_package(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    record = db.scalar(
        select(MapPackage).where(
            MapPackage.company_id == user.company_id,
            MapPackage.active.is_(True),
            MapPackage.deleted_at.is_(None),
        )
    )
    if not record:
        return {"active": False, "package": None, "mode": read_manifest().get("mode", "auto")}
    return {"active": True, "package": _map_package_out(record, _latest_package_validation(db, record.id)), "mode": read_manifest().get("mode", "auto")}


@router.post("/packages/import", status_code=status.HTTP_201_CREATED)
def import_package(payload: MapImportRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    source = Path(payload.source_path).expanduser().resolve()
    validation = _validate_package_file(source, payload, company_id=user.company_id)
    if validation["errors"]:
        raise HTTPException(status_code=422, detail={"message": "Pacote de mapa falhou na validação", "errors": validation["errors"], "checks": validation["checks"]})
    digest = validation["checksum_sha256"]
    stored_name = f"{digest[:16]}{source.suffix.lower()}"
    target = package_path({"stored_name": stored_name})
    if target.exists() and checksum(target) != digest:
        raise HTTPException(status_code=409, detail="Já existe um pacote armazenado com nome incompatível")
    if not target.exists():
        shutil.copy2(source, target)
    record = db.scalar(
        select(MapPackage).where(
            MapPackage.company_id == user.company_id,
            MapPackage.checksum_sha256 == digest,
        )
    )
    metadata = dict(validation["metadata"])
    metadata["tile_format"] = metadata.get("tile_format") or ("pmtiles" if validation["provider"] == "OFFLINE_PMTILES" else "unknown")
    if record is None:
        record = MapPackage(
            company_id=user.company_id,
            provider=validation["provider"],
            original_name=source.name,
            stored_name=stored_name,
            mime_type=validation["mime_type"],
            size_bytes=target.stat().st_size,
            checksum_sha256=digest,
            license=payload.license or validation["license"],
            version=payload.version or "unknown",
            min_zoom=validation["min_zoom"],
            max_zoom=validation["max_zoom"],
            bounds_json=_json_dumps(validation["bounds"]) if validation["bounds"] else None,
            metadata_json=_json_dumps(metadata),
            source=payload.source or "manual",
            status="imported",
            active=False,
            imported_at=utcnow(),
            created_by=user.id,
        )
        db.add(record)
        db.flush()
    else:
        record.provider = validation["provider"]
        record.original_name = source.name
        record.stored_name = stored_name
        record.mime_type = validation["mime_type"]
        record.size_bytes = target.stat().st_size
        record.license = payload.license or validation["license"]
        record.version = payload.version or record.version or "unknown"
        record.min_zoom = validation["min_zoom"]
        record.max_zoom = validation["max_zoom"]
        record.bounds_json = _json_dumps(validation["bounds"]) if validation["bounds"] else None
        record.metadata_json = _json_dumps(metadata)
        record.source = payload.source or record.source or "manual"
        record.deleted_at = None
        record.status = "imported"
        record.updated_by = user.id
    validation_row = _record_package_validation(db, user, record, validation)
    if payload.activate:
        _activate_package_record(db, user, record, "import")
    db.commit()
    db.refresh(record)
    _sync_manifest_record(record)
    return _map_package_out(record, validation_row)


@router.post("/packages/{package_id}/validate")
def validate_package(package_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    path = _package_record_path(record)
    validation = _validate_package_file(path, None, company_id=user.company_id)
    validation_row = _record_package_validation(db, user, record, validation)
    if validation["errors"] and record.active:
        record.active = False
        _sync_manifest_activation(None)
    db.commit()
    db.refresh(record)
    _sync_manifest_record(record)
    return _map_package_out(record, validation_row)


@router.post("/packages/{package_id}/activate")
def activate_package(package_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    _activate_package_record(db, user, record, "manual")
    db.commit()
    db.refresh(record)
    _sync_manifest_record(record)
    return {"message": "Pacote de mapa ativado", "package_id": package_id, "package": _map_package_out(record, _latest_package_validation(db, record.id))}


@router.post("/packages/{package_id}/deactivate")
def deactivate_package_by_id(package_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    _deactivate_package_record(db, user, record, "manual")
    db.commit()
    db.refresh(record)
    _sync_manifest_record(record)
    return {"message": "Pacote de mapa desativado", "package_id": package_id}


@router.post("/packages/deactivate")
def deactivate_package(user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    _deactivate_package_record(db, user, None, "manual")
    db.commit()
    return {"message": "Mapa offline desativado"}


@router.get("/packages/{package_id}/metadata")
def package_metadata(package_id: str, user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    return _map_package_out(record, _latest_package_validation(db, record.id))


@router.delete("/packages/{package_id}")
def remove_package(package_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    path = _package_record_path(record)
    if record.active:
        _deactivate_package_record(db, user, record, "delete")
    record.active = False
    record.status = "deleted"
    record.deleted_at = utcnow()
    record.updated_by = user.id
    if path.exists():
        try:
            path.unlink()
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail="O ficheiro do pacote está em uso. Feche visualizações ativas e tente novamente.") from exc
    db.commit()
    _sync_manifest_record(record)
    return {"message": "Pacote removido"}


@router.get("/packages/{package_id}/pmtiles")
def get_pmtiles(package_id: str, user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    if record.provider != "OFFLINE_PMTILES":
        raise HTTPException(status_code=404, detail="PMTiles não encontrado")
    path = _package_record_path(record)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ficheiro PMTiles não encontrado no armazenamento local")
    _record_package_usage(db, user, record, "pmtiles_archive", f"/maps/packages/{package_id}/pmtiles", path.stat().st_size)
    db.commit()
    return FileResponse(path, media_type="application/octet-stream")


@router.get("/packages/{package_id}/tiles/{z}/{x}/{y}.{extension}")
def get_mbtiles_tile(package_id: str, z: int, x: int, y: int, extension: str, user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    record = _tenant_package(db, user, package_id)
    if record.provider != "OFFLINE_MBTILES":
        raise HTTPException(status_code=404, detail="MBTiles não encontrado")
    path = _package_record_path(record)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ficheiro MBTiles não encontrado no armazenamento local")
    if extension.lower() not in {"pbf", "mvt", "png", "jpg", "jpeg", "webp"}:
        raise HTTPException(status_code=422, detail="Extensão de tile não suportada")
    tms_y = (1 << z) - 1 - y
    conn = sqlite3.connect(path)
    try:
        tables = {table[0] for table in conn.execute("select name from sqlite_master where type='table'")}
        row = conn.execute(
            "select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?",
            (z, x, tms_y),
        ).fetchone()
        metadata = dict(conn.execute("select name, value from metadata").fetchall()) if "metadata" in tables else {}
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Tile não encontrado")
    fmt = str(metadata.get("format") or extension).lower()
    media = {
        "pbf": "application/x-protobuf",
        "mvt": "application/x-protobuf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(fmt, "application/octet-stream")
    _record_package_usage(db, user, record, "mbtiles_tile", f"/maps/packages/{package_id}/tiles/{z}/{x}/{y}.{extension}", len(row[0]))
    db.commit()
    return Response(content=row[0], media_type=media, headers={"Cache-Control": "public, max-age=86400"})
