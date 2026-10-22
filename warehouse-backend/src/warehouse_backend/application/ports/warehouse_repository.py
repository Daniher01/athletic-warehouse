from typing import Protocol
from uuid import UUID

from warehouse_backend.domain.models import Category, Club, FormRecord, Player, WellnessRecord


class WarehouseRepositoryPort(Protocol):
    async def get_player_by_id(self, player_id: UUID) -> Player | None:
        """Lookup player in dim_player by player_id."""
        ...

    async def auto_provision_player(self, player: Player) -> Player:
        """Insert an unverified player into dim_player."""
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

    async def get_club_by_id(self, club_id: UUID) -> Club | None:
        """Lookup club by club_id."""
        ...

    async def get_category_by_id(self, category_id: UUID) -> Category | None:
        """Lookup category by category_id."""
        ...

    async def ping(self) -> bool:
        """Check warehouse connection health."""
        ...
