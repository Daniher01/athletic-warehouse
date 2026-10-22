from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.presentation.api.dependencies import get_warehouse_repository

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    warehouse_connected: bool


@router.get("/health", response_model=HealthResponse)
async def check_health(
    repo: Annotated[WarehouseRepositoryPort, Depends(get_warehouse_repository)],
) -> HealthResponse:
    is_healthy = await repo.ping()
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ClickHouse cluster is unreachable",
        )
    return HealthResponse(status="healthy", warehouse_connected=True)
