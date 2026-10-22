from uuid import UUID

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.domain.models import WellnessRecord


class GetWellnessMetricsUseCase:
    def __init__(self, repository: WarehouseRepositoryPort) -> None:
        self._repo = repository

    async def execute(
        self,
        player_id: UUID | None = None,
        club_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WellnessRecord]:
        return await self._repo.get_wellness_records(
            player_id=player_id,
            club_id=club_id,
            limit=limit,
        )
