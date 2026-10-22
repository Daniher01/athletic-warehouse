from typing import Protocol
from uuid import UUID

from warehouse_backend.domain.models import FormRecord, Player, WellnessRecord


class WarehouseRepositoryPort(Protocol):
    async def get_player_by_id(self, player_id: UUID, club_id: UUID | None = None) -> Player | None:
        """Lookup player in dim_player by player_id, optionally filtered by club_id."""
        ...

    async def get_players_by_ids(self, club_id: UUID, player_ids: list[UUID]) -> dict[UUID, Player]:
        """Batch lookup players in dim_player by club_id and player_ids."""
        ...

    async def auto_provision_player(self, player: Player) -> Player:
        """Insert an unverified player into dim_player."""
        ...

    async def auto_provision_players(self, players: list[Player]) -> list[Player]:
        """Batch insert unverified players into dim_player."""
        ...

    async def insert_raw_records(self, records: list[FormRecord]) -> int:
        """Insert batch of records into Bronze fact_form_records_raw."""
        ...

    async def get_wellness_records(
        self,
        player_id: UUID | None = None,
        club_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WellnessRecord]:
        """Fetch Silver wellness records."""
        ...

    async def ping(self) -> bool:
        """Check warehouse connection health."""
        ...
