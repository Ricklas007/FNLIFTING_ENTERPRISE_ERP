from collections import Counter
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.database.base import Base
from app.database.session import engine
from app.ops.readiness import build_readiness_report
from app.sync import tracking as _sync_tracking  # noqa: F401 — instala os eventos transacionais


REQUEST_TOTAL = Counter()
REQUEST_STATUS_TOTAL = Counter()
REQUEST_LATENCY_MS_SUM = Counter()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API local-first do FNLIFTING Enterprise Management System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.is_production and settings.allowed_host_list and "*" not in settings.allowed_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started_at = perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (perf_counter() - started_at) * 1000
    route = request.url.path
    REQUEST_TOTAL[route] += 1
    REQUEST_STATUS_TOTAL[f"{route}:{response.status_code}"] += 1
    REQUEST_LATENCY_MS_SUM[route] += elapsed_ms
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Process-Time-ms", f"{elapsed_ms:.2f}")
    if settings.security_headers_enabled:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        response.headers.setdefault(
            "Cache-Control",
            "no-store" if request.url.path.startswith(settings.api_v1_prefix) else "no-cache",
        )
    return response


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version, "database": "connected"}


@app.get("/live", tags=["Sistema"])
def live():
    return {"status": "alive", "service": settings.app_name, "version": settings.app_version}


@app.get("/ready", tags=["Sistema"])
def ready():
    report = build_readiness_report()
    if report["status"] != "ready":
        raise HTTPException(status_code=503, detail={"status": report["status"], "summary": report["summary"]})
    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "summary": report["summary"],
    }


@app.get("/metrics", tags=["Sistema"], response_class=PlainTextResponse)
def metrics():
    lines = [
        "# HELP fnlifting_http_requests_total Total de pedidos HTTP por path.",
        "# TYPE fnlifting_http_requests_total counter",
    ]
    for path, count in sorted(REQUEST_TOTAL.items()):
        lines.append(f'fnlifting_http_requests_total{{path="{path}"}} {count}')
    lines.extend([
        "# HELP fnlifting_http_responses_total Total de respostas HTTP por path e status.",
        "# TYPE fnlifting_http_responses_total counter",
    ])
    for key, count in sorted(REQUEST_STATUS_TOTAL.items()):
        path, status_code = key.rsplit(":", 1)
        lines.append(f'fnlifting_http_responses_total{{path="{path}",status="{status_code}"}} {count}')
    lines.extend([
        "# HELP fnlifting_http_request_latency_ms_sum Soma da latência HTTP em ms por path.",
        "# TYPE fnlifting_http_request_latency_ms_sum counter",
    ])
    for path, total in sorted(REQUEST_LATENCY_MS_SUM.items()):
        lines.append(f'fnlifting_http_request_latency_ms_sum{{path="{path}"}} {total:.4f}')
    return "\n".join(lines) + "\n"
