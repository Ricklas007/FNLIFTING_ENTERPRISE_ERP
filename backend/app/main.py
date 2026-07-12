from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.database.base import Base
from app.database.session import engine
from app.ops.readiness import build_readiness_report
from app.sync import tracking as _sync_tracking  # noqa: F401 — instala os eventos transacionais


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
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Process-Time-ms", f"{(perf_counter() - started_at) * 1000:.2f}")
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
