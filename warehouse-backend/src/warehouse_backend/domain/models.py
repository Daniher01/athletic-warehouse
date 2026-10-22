from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    ) -> "Player":
        return cls(
            player_id=player_id,
            club_id=club_id,
            category_id=category_id,
            first_name=first_name,
            last_name=last_name,
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
