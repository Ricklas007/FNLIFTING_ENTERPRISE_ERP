from fastapi import APIRouter

from app.api.routes import admin, auth, dashboard, enterprise, fleet, fleet_tracking, hr, management, maps, operations, portal, system


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(hr.router)
api_router.include_router(operations.router)
api_router.include_router(operations.public_router)
api_router.include_router(fleet.router)
api_router.include_router(fleet_tracking.router)
api_router.include_router(maps.router)
api_router.include_router(management.router)
api_router.include_router(portal.router)
api_router.include_router(system.router)
api_router.include_router(enterprise.router)
