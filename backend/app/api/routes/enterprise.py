from fastapi import APIRouter

from app.api.routes import (
    ai,
    analytics,
    compliance,
    customer_enterprise,
    enterprise_fleet,
    gps,
    hr_enterprise,
    licensing,
    notifications,
    ocr,
    payroll,
    rules,
    security,
    sync,
    tenancy,
)


router = APIRouter(prefix="/enterprise", tags=["Fases 8-12 · Enterprise"])
router.include_router(tenancy.router)
router.include_router(security.router)
router.include_router(sync.router)
router.include_router(notifications.router)
router.include_router(enterprise_fleet.router)
router.include_router(gps.router)
router.include_router(ai.router)
router.include_router(ocr.router)
router.include_router(rules.router)
router.include_router(hr_enterprise.router)
router.include_router(payroll.router)
router.include_router(analytics.router)
router.include_router(compliance.router)
router.include_router(customer_enterprise.router)
router.include_router(licensing.router)
