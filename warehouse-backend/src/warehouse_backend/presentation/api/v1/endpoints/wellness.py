from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from warehouse_backend.application.use_cases.get_wellness_metrics import GetWellnessMetricsUseCase
from warehouse_backend.domain.auth.models import AuthenticatedUser, DepartmentRole
from warehouse_backend.domain.models import WellnessRecord
from warehouse_backend.presentation.api.dependencies import (
    get_wellness_metrics_use_case,
    require_role,
)

router = APIRouter(prefix="/wellness", tags=["Wellness Metrics"])


@router.get("", response_model=list[WellnessRecord])
async def list_wellness_records(
    use_case: Annotated[GetWellnessMetricsUseCase, Depends(get_wellness_metrics_use_case)],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_role(DepartmentRole.ANALYST, DepartmentRole.ADMIN)),
    ],
    player_id: UUID | None = Query(default=None, description="Filter by player UUID"),
    club_id: UUID | None = Query(default=None, description="Filter by club UUID"),
    limit: int = Query(default=50, ge=1, le=500, description="Max rows to return"),
) -> list[WellnessRecord]:
    """Retrieve processed wellness metrics. Requires dept_analyst or dept_admin role."""
    return await use_case.execute(player_id=player_id, club_id=club_id, limit=limit)
