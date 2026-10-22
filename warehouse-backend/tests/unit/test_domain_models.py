from datetime import date
from uuid import UUID, uuid4

from warehouse_backend.domain.exceptions import MissingPlayerIdError, PlayerNotFoundError
from warehouse_backend.domain.models import (
    FormRecord,
    Player,
    PlayerStatus,
    generate_player_id,
    generate_player_slug,
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


def test_generate_player_slug_standard_cases() -> None:
    # Nico Williams born 12/07/2002 -> nw-12072002
    assert generate_player_slug("Nico", "Williams", date(2002, 7, 12)) == "nw-12072002"

    # Iñaki Williams born 15/06/1994 -> iw-15061994 (strips tilde on ñ)
    assert generate_player_slug("Iñaki", "Williams", date(1994, 6, 15)) == "iw-15061994"

    # Unai Simón born 11/06/1997 -> us-11061997 (strips accent on ó)
    assert generate_player_slug("Unai", "Simón", date(1997, 6, 11)) == "us-11061997"

    # Mikel Jauregizar born 13/11/2003 -> mj-13112003
    assert generate_player_slug("Mikel", "Jauregizar", date(2003, 11, 13)) == "mj-13112003"


def test_generate_player_slug_compound_names() -> None:
    # Compound names with hyphens and spaces
    slug = generate_player_slug("Jon Ander", "Gómez-Pérez", date(2001, 3, 5))
    assert slug == "jagp-05032001"


def test_generate_player_id_determinism() -> None:
    club_id = UUID("11111111-1111-1111-1111-111111111111")
    slug = "nw-12072002"

    id1 = generate_player_id(club_id, slug)
    id2 = generate_player_id(club_id, slug)
    id3 = generate_player_id(club_id, "NW-12072002 ")

    # Deterministic and case/whitespace-insensitive
    assert id1 == id2
    assert id1 == id3

    # Different slug yields different ID
    other_slug_id = generate_player_id(club_id, "iw-15061994")
    assert id1 != other_slug_id

    # Different club yields different ID
    other_club_id = UUID("99999999-9999-9999-9999-999999999999")
    different_club_player_id = generate_player_id(other_club_id, slug)
    assert id1 != different_club_player_id
