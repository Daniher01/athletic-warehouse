import json
from typing import Any
from uuid import UUID

from clickhouse_connect.driver.client import Client

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.domain.models import (
    FormRecord,
    Player,
    PlayerStatus,
    WellnessRecord,
)


class ClickHouseWarehouseRepository(WarehouseRepositoryPort):
    def __init__(self, client: Client) -> None:
        self._client = client

    async def ping(self) -> bool:
        try:
            res = self._client.command("SELECT 1")
            return res == 1 or res == "1"
        except Exception:
            return False

    async def get_player_by_id(self, player_id: UUID, club_id: UUID | None = None) -> Player | None:
        where_parts = ["player_id = %(player_id)s"]
        params: dict[str, Any] = {"player_id": str(player_id)}
        if club_id is not None:
            where_parts.append("club_id = %(club_id)s")
            params["club_id"] = str(club_id)

        query = f"""
        SELECT
            player_id, club_id, category_id, first_name, last_name,
            nationality, birth_date, position, status, created_at, updated_at
        FROM dim_player FINAL
        WHERE {" AND ".join(where_parts)}
        LIMIT 1
        """
        result = self._client.query(query, parameters=params)
        rows = result.result_rows
        if not rows:
            return None

        row = rows[0]
        return Player(
            player_id=row[0],
            club_id=row[1],
            category_id=row[2],
            first_name=row[3],
            last_name=row[4],
            nationality=row[5],
            birth_date=row[6],
            position=row[7],
            status=PlayerStatus(row[8]),
            created_at=row[9],
            updated_at=row[10],
        )

    async def get_players_by_ids(self, club_id: UUID, player_ids: list[UUID]) -> dict[UUID, Player]:
        if not player_ids:
            return {}

        query = """
        SELECT
            player_id, club_id, category_id, first_name, last_name,
            nationality, birth_date, position, status, created_at, updated_at
        FROM dim_player FINAL
        WHERE club_id = %(club_id)s AND player_id IN %(player_ids)s
        """
        result = self._client.query(
            query,
            parameters={
                "club_id": str(club_id),
                "player_ids": [str(pid) for pid in player_ids],
            },
        )
        players: dict[UUID, Player] = {}
        for row in result.result_rows:
            p = Player(
                player_id=row[0],
                club_id=row[1],
                category_id=row[2],
                first_name=row[3],
                last_name=row[4],
                nationality=row[5],
                birth_date=row[6],
                position=row[7],
                status=PlayerStatus(row[8]),
                created_at=row[9],
                updated_at=row[10],
            )
            players[p.player_id] = p
        return players

    async def auto_provision_player(self, player: Player) -> Player:
        provisioned = await self.auto_provision_players([player])
        return provisioned[0]

    async def auto_provision_players(self, players: list[Player]) -> list[Player]:
        if not players:
            return []

        columns = [
            "player_id",
            "club_id",
            "category_id",
            "first_name",
            "last_name",
            "nationality",
            "birth_date",
            "position",
            "status",
            "created_at",
            "updated_at",
        ]
        data = [
            [
                str(player.player_id),
                str(player.club_id),
                str(player.category_id),
                player.first_name,
                player.last_name,
                player.nationality,
                player.birth_date,
                player.position,
                player.status.value,
                player.created_at,
                player.updated_at,
            ]
            for player in players
        ]
        self._client.insert("dim_player", data, column_names=columns)
        return players

    async def insert_raw_records(self, records: list[FormRecord]) -> int:
        if not records:
            return 0

        columns = [
            "record_id",
            "club_id",
            "department_id",
            "form_name",
            "player_id",
            "category_id",
            "metric_date",
            "ingested_at",
            "raw_data",
        ]
        data: list[list[Any]] = []
        for rec in records:
            raw_str = (
                json.dumps(rec.raw_data) if isinstance(rec.raw_data, dict) else str(rec.raw_data)
            )
            data.append(
                [
                    str(rec.record_id),
                    str(rec.club_id),
                    rec.department_id,
                    rec.form_name,
                    str(rec.player_id),
                    str(rec.category_id),
                    rec.metric_date,
                    rec.ingested_at,
                    raw_str,
                ]
            )

        self._client.insert("fact_form_records_raw", data, column_names=columns)
        return len(records)

    async def get_wellness_records(
        self,
        player_id: UUID | None = None,
        club_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WellnessRecord]:
        where_clauses: list[str] = []
        params: dict[str, Any] = {"limit": limit}

        if player_id:
            where_clauses.append("player_id = %(player_id)s")
            params["player_id"] = str(player_id)
        if club_id:
            where_clauses.append("club_id = %(club_id)s")
            params["club_id"] = str(club_id)

        where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
        SELECT
            record_id, club_id, player_id, category_id, metric_date,
            rpe, sleep_quality, muscle_soreness, stress_level, fatigue_level,
            notes, ingested_at
        FROM fact_wellness_records FINAL
        {where_stmt}
        ORDER BY metric_date DESC, ingested_at DESC
        LIMIT %(limit)s
        """
        result = self._client.query(query, parameters=params)
        records: list[WellnessRecord] = []
        for row in result.result_rows:
            records.append(
                WellnessRecord(
                    record_id=row[0],
                    club_id=row[1],
                    player_id=row[2],
                    category_id=row[3],
                    metric_date=row[4],
                    rpe=row[5],
                    sleep_quality=row[6],
                    muscle_soreness=row[7],
                    stress_level=row[8],
                    fatigue_level=row[9],
                    notes=row[10],
                    ingested_at=row[11],
                )
            )
        return records
