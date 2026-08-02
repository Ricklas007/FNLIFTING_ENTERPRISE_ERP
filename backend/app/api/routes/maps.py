import hashlib
import json
import logging
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
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import MAP_CACHE_DIR, MAP_DIR
from app.database.session import get_db
from app.models import AuditLog, User


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
    try:
        with sqlite3.connect(path) as conn:
            tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
            if "tiles" not in tables:
                raise HTTPException(status_code=422, detail="MBTiles sem tabela tiles")
            metadata = dict(conn.execute("select name, value from metadata").fetchall()) if "metadata" in tables else {}
            if metadata.get("format") not in {None, "pbf", "mvt", "png", "jpg", "jpeg", "webp"}:
                raise HTTPException(status_code=422, detail="Formato MBTiles nÃ£o suportado")
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=422, detail="MBTiles invÃ¡lido ou corrompido") from exc
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
    mode = manifest.get("mode", "auto")
    active = next((item for item in manifest["packages"] if item["id"] == manifest.get("active_package_id")), None)
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
            "OFFLINE_PMTILES": {"available": any(item["provider"] == "OFFLINE_PMTILES" for item in manifest["packages"])},
            "OFFLINE_MBTILES": {"available": any(item["provider"] == "OFFLINE_MBTILES" for item in manifest["packages"])},
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
        raise HTTPException(status_code=404, detail="Pacote de mapa nÃ£o encontrado")
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
        raise HTTPException(status_code=404, detail="Pacote de mapa nÃ£o encontrado")
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
        raise HTTPException(status_code=404, detail="PMTiles nÃ£o encontrado")
    return FileResponse(package_path(record), media_type="application/octet-stream")


@router.get("/packages/{package_id}/tiles/{z}/{x}/{y}.{extension}")
def get_mbtiles_tile(package_id: str, z: int, x: int, y: int, extension: str):
    manifest = read_manifest()
    record = next((item for item in manifest["packages"] if item["id"] == package_id), None)
    if not record or record["provider"] != "OFFLINE_MBTILES":
        raise HTTPException(status_code=404, detail="MBTiles nÃ£o encontrado")
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
        raise HTTPException(status_code=404, detail="Tile nÃ£o encontrado")
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
