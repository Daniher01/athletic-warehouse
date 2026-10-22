from datetime import date
from uuid import UUID, uuid4

import pytest

from tests.conftest import InMemoryWarehouseRepository
from warehouse_backend.application.use_cases.ingest_records import IngestTableflowRecordsUseCase
from warehouse_backend.domain.exceptions import MissingPlayerIdError
from warehouse_backend.domain.models import FormRecord, PlayerStatus


@pytest.mark.asyncio
async def test_ingest_empty_records(in_memory_repo: InMemoryWarehouseRepository) -> None:
    use_case = IngestTableflowRecordsUseCase(in_memory_repo)
    result = await use_case.execute([], default_category_id=uuid4())

    assert result.records_processed == 0
    assert result.records_inserted == 0
    assert result.players_provisioned == 0


@pytest.mark.asyncio
async def test_ingest_existing_verified_player(in_memory_repo: InMemoryWarehouseRepository) -> None:
    use_case = IngestTableflowRecordsUseCase(in_memory_repo)
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    player_id = UUID("33333333-3333-3333-3333-333333333301")

    record = FormRecord(
        club_id=club_id,
        department_id="preparacion_fisica",
        form_name="wellness",
        player_id=player_id,
        category_id=cat_id,
        metric_date=date(2026, 10, 22),
        raw_data={"rpe": 7},
    )

    result = await use_case.execute([record], default_category_id=cat_id)

    assert result.records_processed == 1
    assert result.records_inserted == 1
    assert result.players_provisioned == 0


@pytest.mark.asyncio
async def test_ingest_unknown_player_auto_provisions(
    in_memory_repo: InMemoryWarehouseRepository,
) -> None:
    use_case = IngestTableflowRecordsUseCase(in_memory_repo)
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    unknown_player_id = uuid4()

    record = FormRecord(
        club_id=club_id,
        department_id="preparacion_fisica",
        form_name="wellness",
        player_id=unknown_player_id,
        category_id=cat_id,
        metric_date=date(2026, 10, 22),
        raw_data={"rpe": 8},
    )

    result = await use_case.execute([record], default_category_id=cat_id)

    assert result.records_processed == 1
    assert result.records_inserted == 1
    assert result.players_provisioned == 1

    provisioned_player = in_memory_repo.players.get(unknown_player_id)
    assert provisioned_player is not None
    assert provisioned_player.status == PlayerStatus.UNVERIFIED


@pytest.mark.asyncio
async def test_ingest_missing_player_id_raises_error(
    in_memory_repo: InMemoryWarehouseRepository,
) -> None:
    use_case = IngestTableflowRecordsUseCase(in_memory_repo)
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")

    record = FormRecord(
        club_id=club_id,
        department_id="preparacion_fisica",
        form_name="wellness",
        player_id=UUID(int=0),
        category_id=cat_id,
        metric_date=date(2026, 10, 22),
        raw_data={"rpe": 8},
    )

    with pytest.raises(MissingPlayerIdError):
        await use_case.execute([record], default_category_id=cat_id)


@pytest.mark.asyncio
async def test_ingest_batch_multiple_players_auto_provisions(
    in_memory_repo: InMemoryWarehouseRepository,
) -> None:
    use_case = IngestTableflowRecordsUseCase(in_memory_repo)
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    cat_id = UUID("22222222-2222-2222-2222-222222222201")
    existing_id = UUID("33333333-3333-3333-3333-333333333301")
    new_id_1 = uuid4()
    new_id_2 = uuid4()

    records = [
        FormRecord(
            club_id=club_id,
            department_id="preparacion_fisica",
            form_name="wellness",
            player_id=existing_id,
            category_id=cat_id,
            metric_date=date(2026, 10, 22),
            raw_data={"rpe": 6},
        ),
        FormRecord(
            club_id=club_id,
            department_id="preparacion_fisica",
            form_name="wellness",
            player_id=new_id_1,
            category_id=cat_id,
            metric_date=date(2026, 10, 22),
            raw_data={"rpe": 7},
        ),
        FormRecord(
            club_id=club_id,
            department_id="preparacion_fisica",
            form_name="wellness",
            player_id=new_id_2,
            category_id=cat_id,
            metric_date=date(2026, 10, 22),
            raw_data={"rpe": 8},
        ),
    ]

    result = await use_case.execute(records, default_category_id=cat_id)

    assert result.records_processed == 3
    assert result.records_inserted == 3
    assert result.players_provisioned == 2
    assert in_memory_repo.players[new_id_1].status == PlayerStatus.UNVERIFIED
    assert in_memory_repo.players[new_id_2].status == PlayerStatus.UNVERIFIED
