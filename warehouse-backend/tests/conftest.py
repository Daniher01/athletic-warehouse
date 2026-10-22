from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
import pytest
from clickhouse_connect.driver.client import Client
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from warehouse_backend.application.auth.interfaces import TokenVerifierPort
from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.config import Settings
from warehouse_backend.domain.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from warehouse_backend.domain.auth.models import AuthenticatedUser
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
    get_token_verifier,
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


# Generate RSA key pair once for test signing
_TEST_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()


def create_test_jwt(
    sub: str = "test-user-id",
    username: str = "test_user",
    roles: list[str] | None = None,
    groups: list[str] | None = None,
    department_id: str | None = None,
    issuer: str = "http://localhost:8080/realms/sports-club",
    audience: str = "warehouse-backend-api",
    expires_in_seconds: int = 3600,
    private_key: Any = None,
) -> str:
    key_to_use = private_key or _TEST_PRIVATE_KEY
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": sub,
        "preferred_username": username,
        "email": f"{username}@example.com",
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "realm_access": {"roles": roles or []},
        "groups": groups or [],
    }
    if department_id:
        payload["department_id"] = department_id

    headers = {"kid": "test-key-id", "alg": "RS256"}
    return jwt.encode(payload, key_to_use, algorithm="RS256", headers=headers)


class MockTokenVerifier(TokenVerifierPort):
    """Token verifier implementation for test suites verifying against _TEST_PUBLIC_KEY."""

    def __init__(self, expected_issuer: str = "http://localhost:8080/realms/sports-club") -> None:
        self.expected_issuer = expected_issuer

    async def verify_token(self, token: str) -> AuthenticatedUser:
        if not token:
            raise InvalidTokenError("Empty token.")

        try:
            payload = jwt.decode(
                token,
                _TEST_PUBLIC_KEY,
                algorithms=["RS256"],
                audience="warehouse-backend-api",
                issuer=self.expected_issuer,
            )
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired.") from e
        except Exception as e:
            raise InvalidTokenError(str(e)) from e

        roles = set(payload.get("realm_access", {}).get("roles", []))
        groups = tuple(payload.get("groups", []))
        departments: set[str] = set()

        for group in groups:
            parts = [p.strip().lower() for p in group.strip("/").split("/") if p.strip()]
            if "departamentos" in parts:
                idx = parts.index("departamentos") + 1
                if idx < len(parts):
                    departments.add(parts[idx])
            elif parts:
                departments.add(parts[-1])

        if "department_id" in payload:
            departments.add(str(payload["department_id"]).strip().lower())

        return AuthenticatedUser(
            user_id=str(payload["sub"]),
            username=str(payload.get("preferred_username", payload["sub"])),
            email=payload.get("email"),
            roles=frozenset(roles),
            groups=groups,
            departments=frozenset(departments),
        )


@pytest.fixture
def mock_verifier() -> MockTokenVerifier:
    return MockTokenVerifier()


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
def test_client(
    in_memory_repo: InMemoryWarehouseRepository,
    mock_verifier: MockTokenVerifier,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_warehouse_repository] = lambda: in_memory_repo
    app.dependency_overrides[get_token_verifier] = lambda: mock_verifier
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
