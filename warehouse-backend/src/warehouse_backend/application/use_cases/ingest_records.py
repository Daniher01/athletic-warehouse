from dataclasses import dataclass
from uuid import UUID

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.domain.exceptions import MissingPlayerIdError
from warehouse_backend.domain.models import FormRecord, Player


@dataclass
class IngestionResult:
    records_processed: int
    records_inserted: int
    players_provisioned: int


class IngestTableflowRecordsUseCase:
    def __init__(self, repository: WarehouseRepositoryPort) -> None:
        self._repo = repository

    async def execute(
        self,
        records: list[FormRecord],
        default_category_id: UUID,
    ) -> IngestionResult:
        if not records:
            return IngestionResult(0, 0, 0)

        provisioned_count = 0
        checked_players: dict[UUID, bool] = {}

        for idx, rec in enumerate(records):
            if not rec.player_id or rec.player_id == UUID(int=0):
                raise MissingPlayerIdError(record_index=idx)

            if rec.player_id not in checked_players:
                existing_player = await self._repo.get_player_by_id(rec.player_id)
                if existing_player is None:
                    unverified_player = Player.create_unverified(
                        player_id=rec.player_id,
                        club_id=rec.club_id,
                        category_id=rec.category_id or default_category_id,
                        first_name=f"Player-{str(rec.player_id)[:8]}",
                        last_name="Unverified",
                    )
                    await self._repo.auto_provision_player(unverified_player)
                    provisioned_count += 1
                checked_players[rec.player_id] = True

        inserted = await self._repo.insert_raw_records(records)
        return IngestionResult(
            records_processed=len(records),
            records_inserted=inserted,
            players_provisioned=provisioned_count,
        )
