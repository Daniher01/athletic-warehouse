from datetime import date
from uuid import UUID, uuid4

import pytest

from warehouse_backend.domain.models import FormRecord, Player, PlayerStatus
from warehouse_backend.infrastructure.clickhouse.repository import ClickHouseWarehouseRepository


@pytest.mark.asyncio
async def test_clickhouse_ping(live_repository: ClickHouseWarehouseRepository) -> None:
    is_alive = await live_repository.ping()
    assert is_alive is True


@pytest.mark.asyncio
async def test_get_players_by_ids_batch(live_repository: ClickHouseWarehouseRepository) -> None:
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    player_id_1 = UUID("33333333-3333-3333-3333-333333333301")
    player_id_2 = UUID("33333333-3333-3333-3333-333333333302")
    missing_id = uuid4()

    players = await live_repository.get_players_by_ids(
        club_id=club_id,
        player_ids=[player_id_1, player_id_2, missing_id],
    )

    assert len(players) == 2
    assert player_id_1 in players
    assert player_id_2 in players
    assert missing_id not in players
    assert players[player_id_1].first_name == "Iñaki"
    assert players[player_id_2].first_name == "Nico"


@pytest.mark.asyncio
async def test_auto_provision_players_batch(
    live_repository: ClickHouseWarehouseRepository,
) -> None:
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    p1_id = uuid4()
    p2_id = uuid4()

    p1 = Player.create_unverified(
        player_id=p1_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="BatchPlayer1",
        last_name="Unverified",
    )
    p2 = Player.create_unverified(
        player_id=p2_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="BatchPlayer2",
        last_name="Unverified",
    )

    provisioned = await live_repository.auto_provision_players([p1, p2])
    assert len(provisioned) == 2

    fetched = await live_repository.get_players_by_ids(club_id, [p1_id, p2_id])
    assert p1_id in fetched
    assert p2_id in fetched
    assert fetched[p1_id].status == PlayerStatus.UNVERIFIED
    assert fetched[p2_id].status == PlayerStatus.UNVERIFIED


@pytest.mark.asyncio
async def test_get_seed_player(live_repository: ClickHouseWarehouseRepository) -> None:
    player_id = UUID("33333333-3333-3333-3333-333333333301")
    player = await live_repository.get_player_by_id(player_id)

    assert player is not None
    assert player.player_id == player_id
    assert player.first_name == "Iñaki"
    assert player.last_name == "Williams"
    assert player.status == PlayerStatus.VERIFIED


@pytest.mark.asyncio
async def test_auto_provision_unverified_player(
    live_repository: ClickHouseWarehouseRepository,
) -> None:
    new_player_id = uuid4()
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    category_id = UUID("22222222-2222-2222-2222-222222222201")

    unverified = Player.create_unverified(
        player_id=new_player_id,
        club_id=club_id,
        category_id=category_id,
        first_name="TestUnverified",
        last_name="Player",
    )

    saved = await live_repository.auto_provision_player(unverified)
    assert saved.player_id == new_player_id

    fetched = await live_repository.get_player_by_id(new_player_id)
    assert fetched is not None
    assert fetched.player_id == new_player_id
    assert fetched.status == PlayerStatus.UNVERIFIED


@pytest.mark.asyncio
async def test_insert_raw_and_streaming_silver_read(
    live_repository: ClickHouseWarehouseRepository,
) -> None:
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    test_player_id = uuid4()
    record_id = uuid4()
    metric_date = date(2026, 10, 22)

    # First auto-provision the test player
    unverified = Player.create_unverified(
        player_id=test_player_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="Streaming",
        last_name="Tester",
    )
    await live_repository.auto_provision_player(unverified)

    raw_data = {
        "rpe": 9,
        "sleep_quality": 8,
        "muscle_soreness": 2,
        "stress_level": 3,
        "fatigue_level": 4,
        "notes": "Excellent readiness",
    }

    form_record = FormRecord(
        record_id=record_id,
        club_id=club_id,
        department_id="preparacion_fisica",
        form_name="wellness",
        player_id=test_player_id,
        category_id=cat_id,
        metric_date=metric_date,
        raw_data=raw_data,
    )

    inserted_count = await live_repository.insert_raw_records([form_record])
    assert inserted_count == 1

    # Verify that ClickHouse streaming Materialized View triggered Silver insertion
    wellness_records = await live_repository.get_wellness_records(
        player_id=test_player_id, limit=10
    )
    assert len(wellness_records) >= 1

    matching = next((r for r in wellness_records if r.record_id == record_id), None)
    assert matching is not None
    assert matching.rpe == 9
    assert matching.sleep_quality == 8
    assert matching.notes == "Excellent readiness"
