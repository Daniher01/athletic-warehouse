import re
import unicodedata
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from pydantic import BaseModel, Field


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_player_slug(first_name: str, last_name: str, birth_date: date) -> str:
    """Generate deterministic player slug formatted as [initials]-[DDMMYYYY].

    Strips accents/diacritics and non-alphanumeric noise.
    Example: 'Nico', 'Williams', 2002-07-12 -> 'nw-12072002'
             'Iñaki', 'Williams', 1994-06-15 -> 'iw-15061994'
             'Unai', 'Simón', 1997-06-11 -> 'us-11061997'
    """

    def _extract_initials(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        words = [w for w in re.split(r"[\s\-]+", ascii_text.strip()) if w]
        return "".join(w[0].lower() for w in words if w[0].isalnum())

    first_init = _extract_initials(first_name)
    last_init = _extract_initials(last_name)
    initials = f"{first_init}{last_init}" or "xx"
    date_part = birth_date.strftime("%d%m%Y")
    return f"{initials}-{date_part}"


def generate_player_id(club_id: UUID, player_slug: str) -> UUID:
    """Derive deterministic UUIDv5 for a player within a club namespace."""
    normalized_slug = player_slug.strip().lower()
    return uuid5(NAMESPACE_DNS, f"{club_id}:{normalized_slug}")


class PlayerStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class Club(BaseModel):
    club_id: UUID
    name: str
    country: str
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)


class Category(BaseModel):
    category_id: UUID
    club_id: UUID
    name: str
    sort_order: int
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)


class Player(BaseModel):
    player_id: UUID
    club_id: UUID
    category_id: UUID
    first_name: str
    last_name: str
    nationality: str = "Spain"
    birth_date: date = Field(default_factory=lambda: date(2000, 1, 1))
    position: str = "Unknown"
    status: PlayerStatus = PlayerStatus.VERIFIED
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @classmethod
    def create_unverified(
        cls,
        player_id: UUID,
        club_id: UUID,
        category_id: UUID,
        first_name: str = "Auto-Provisioned",
        last_name: str = "Player",
        birth_date: date | None = None,
        nationality: str = "Spain",
        position: str = "Unknown",
    ) -> "Player":
        return cls(
            player_id=player_id,
            club_id=club_id,
            category_id=category_id,
            first_name=first_name,
            last_name=last_name,
            nationality=nationality,
            birth_date=birth_date or date(2000, 1, 1),
            position=position,
            status=PlayerStatus.UNVERIFIED,
        )


class FormRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    club_id: UUID
    department_id: str
    form_name: str
    player_id: UUID
    category_id: UUID
    metric_date: date
    raw_data: dict[str, Any] | str
    ingested_at: datetime = Field(default_factory=get_utc_now)


class WellnessRecord(BaseModel):
    record_id: UUID
    club_id: UUID
    player_id: UUID
    category_id: UUID
    metric_date: date
    rpe: int | None = None
    sleep_quality: int | None = None
    muscle_soreness: int | None = None
    stress_level: int | None = None
    fatigue_level: int | None = None
    notes: str | None = None
    ingested_at: datetime
