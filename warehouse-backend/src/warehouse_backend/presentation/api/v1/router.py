from fastapi import APIRouter

from warehouse_backend.presentation.api.v1.endpoints.auth import router as auth_router
from warehouse_backend.presentation.api.v1.endpoints.health import router as health_router
from warehouse_backend.presentation.api.v1.endpoints.ingest import router as ingest_router
from warehouse_backend.presentation.api.v1.endpoints.wellness import router as wellness_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(ingest_router)
api_v1_router.include_router(wellness_router)
