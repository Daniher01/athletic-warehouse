from collections.abc import Generator
from uuid import UUID

import pytest
from clickhouse_connect.driver.client import Client
from fastapi.testclient import TestClient

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.config import Settings
from warehouse_backend.domain.models import (
    Category,
    Club,
    FormRecord,
    Player,
    PlayerStatus,
    WellnessRecord,
)
from warehouse_backend.infrastructure.clickhouse.client import create_clickhouse_client
from warehouse_backend.infrastructure.clickhouse.repository import ClickHouseWarehouseRepository
from warehouse_backend.main import app
from warehouse_backend.presentation.api.dependencies import (
    get_warehouse_repository,
)


class InMemoryWarehouseRepository(WarehouseRepositoryPort):
    def __init__(self) -> None:
        self.players: dict[UUID, Player] = {}
        self.clubs: dict[UUID, Club] = {}
        self.categories: dict[UUID, Category] = {}
        self.raw_records: list[FormRecord] = []
        self.wellness_records: list[WellnessRecord] = []

    async def ping(self) -> bool:
        return True

    async def get_player_by_id(self, player_id: UUID) -> Player | None:
        return self.players.get(player_id)

    async def auto_provision_player(self, player: Player) -> Player:
        self.players[player.player_id] = player
        return player

    async def insert_raw_records(self, records: list[FormRecord]) -> int:
        self.raw_records.extend(records)
        return len(records)

    async def get_wellness_records(
        self,
        player_id: UUID | None = None,
        club_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WellnessRecord]:
        results = self.wellness_records
        if player_id:
            results = [r for r in results if r.player_id == player_id]
        if club_id:
            results = [r for r in results if r.club_id == club_id]
        return results[:limit]

    async def get_club_by_id(self, club_id: UUID) -> Club | None:
        return self.clubs.get(club_id)

    async def get_category_by_id(self, category_id: UUID) -> Category | None:
        return self.categories.get(category_id)


@pytest.fixture
def in_memory_repo() -> InMemoryWarehouseRepository:
    repo = InMemoryWarehouseRepository()
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    player_id = UUID("33333333-3333-3333-3333-333333333301")

    repo.clubs[club_id] = Club(club_id=club_id, name="Athletic Club", country="Spain")
    repo.categories[cat_id] = Category(
        category_id=cat_id, club_id=club_id, name="Primer Equipo", sort_order=1
    )
    repo.players[player_id] = Player(
        player_id=player_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="Iñaki",
        last_name="Williams",
        status=PlayerStatus.VERIFIED,
    )
    return repo


@pytest.fixture
def test_client(in_memory_repo: InMemoryWarehouseRepository) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_warehouse_repository] = lambda: in_memory_repo
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def clickhouse_client() -> Client:
    settings = Settings()
    return create_clickhouse_client(settings)


@pytest.fixture
def live_repository(clickhouse_client: Client) -> ClickHouseWarehouseRepository:
    return ClickHouseWarehouseRepository(clickhouse_client)
