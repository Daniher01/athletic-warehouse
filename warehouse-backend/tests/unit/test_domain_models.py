from datetime import date
from uuid import uuid4

from warehouse_backend.domain.exceptions import MissingPlayerIdError, PlayerNotFoundError
from warehouse_backend.domain.models import (
    FormRecord,
    Player,
    PlayerStatus,
)


def test_player_creation_and_defaults() -> None:
    player_id = uuid4()
    club_id = uuid4()
    cat_id = uuid4()

    player = Player(
        player_id=player_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="Nico",
        last_name="Williams",
    )

    assert player.player_id == player_id
    assert player.status == PlayerStatus.VERIFIED
    assert player.nationality == "Spain"
    assert player.birth_date == date(2000, 1, 1)


def test_player_create_unverified() -> None:
    player_id = uuid4()
    club_id = uuid4()
    cat_id = uuid4()

    player = Player.create_unverified(
        player_id=player_id,
        club_id=club_id,
        category_id=cat_id,
        first_name="Auto",
        last_name="Unverified",
    )

    assert player.player_id == player_id
    assert player.status == PlayerStatus.UNVERIFIED
    assert player.first_name == "Auto"
    assert player.last_name == "Unverified"


def test_missing_player_id_error_formatting() -> None:
    err_with_idx = MissingPlayerIdError(record_index=3)
    assert "Record at index 3" in str(err_with_idx)

    err_without_idx = MissingPlayerIdError()
    assert "Form record is missing" in str(err_without_idx)


def test_player_not_found_error() -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    err = PlayerNotFoundError(fake_id)
    assert fake_id in str(err)


def test_form_record_initialization() -> None:
    record = FormRecord(
        club_id=uuid4(),
        department_id="medico",
        form_name="wellness",
        player_id=uuid4(),
        category_id=uuid4(),
        metric_date=date(2026, 10, 22),
        raw_data={"rpe": 5, "notes": "good"},
    )
    assert record.department_id == "medico"
    assert isinstance(record.raw_data, dict)
