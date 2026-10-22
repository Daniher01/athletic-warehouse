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

        # 1. Invariant check: validate player_id presence
        club_player_ids: dict[UUID, set[UUID]] = {}
        player_category_map: dict[UUID, UUID] = {}

        for idx, rec in enumerate(records):
            if not rec.player_id or rec.player_id == UUID(int=0):
                raise MissingPlayerIdError(record_index=idx)

            club_player_ids.setdefault(rec.club_id, set()).add(rec.player_id)
            if rec.player_id not in player_category_map:
                player_category_map[rec.player_id] = rec.category_id or default_category_id

        # 2. Batch check existing players in OLAP warehouse per club
        new_players_to_provision: list[Player] = []
        for club_id, pids in club_player_ids.items():
            existing = await self._repo.get_players_by_ids(club_id, list(pids))
            missing_ids = pids - set(existing.keys())

            for pid in missing_ids:
                cat_id = player_category_map.get(pid, default_category_id)
                unverified_player = Player.create_unverified(
                    player_id=pid,
                    club_id=club_id,
                    category_id=cat_id,
                    first_name=f"Player-{str(pid)[:8]}",
                    last_name="Unverified",
                )
                new_players_to_provision.append(unverified_player)

        # 3. Batch auto-provision missing players
        if new_players_to_provision:
            await self._repo.auto_provision_players(new_players_to_provision)

        # 4. Atomic batch insertion into Bronze layer
        inserted = await self._repo.insert_raw_records(records)

        return IngestionResult(
            records_processed=len(records),
            records_inserted=inserted,
            players_provisioned=len(new_players_to_provision),
        )
