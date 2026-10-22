from typing import Any
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import _TEST_PUBLIC_KEY, create_test_jwt
from warehouse_backend.domain.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from warehouse_backend.infrastructure.auth.keycloak_verifier import KeycloakJwtVerifier


class DummySigningKey:
    def __init__(self, key: Any) -> None:
        self.key = key


@pytest.fixture
def mock_jwk_client() -> MagicMock:
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = DummySigningKey(_TEST_PUBLIC_KEY)
    return client


@pytest.fixture
def verifier(mock_jwk_client: MagicMock) -> KeycloakJwtVerifier:
    return KeycloakJwtVerifier(
        jwks_url="http://localhost:8080/realms/sports-club/protocol/openid-connect/certs",
        valid_issuers=[
            "http://localhost:8080/realms/sports-club",
            "http://keycloak:8080/realms/sports-club",
        ],
        audience="warehouse-backend-api",
        jwk_client=mock_jwk_client,
    )


@pytest.mark.asyncio
async def test_verifier_valid_token(verifier: KeycloakJwtVerifier) -> None:
    token = create_test_jwt(
        sub="user-456",
        username="mikel_coach",
        roles=["dept_analyst"],
        groups=["/Departamentos/Preparacion-Fisica"],
        issuer="http://localhost:8080/realms/sports-club",
        audience="warehouse-backend-api",
    )

    user = await verifier.verify_token(token)
    assert user.user_id == "user-456"
    assert user.username == "mikel_coach"
    assert "dept_analyst" in user.roles
    assert "preparacion-fisica" in user.departments
    assert user.has_department("preparacion-fisica") is True


@pytest.mark.asyncio
async def test_verifier_expired_token(verifier: KeycloakJwtVerifier) -> None:
    token = create_test_jwt(
        expires_in_seconds=-10,  # Expired in past
    )

    with pytest.raises(TokenExpiredError) as exc_info:
        await verifier.verify_token(token)
    assert "expired" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_verifier_invalid_issuer(verifier: KeycloakJwtVerifier) -> None:
    token = create_test_jwt(
        issuer="http://rogue-issuer.internal/realms/malicious",
    )

    with pytest.raises(InvalidTokenError) as exc_info:
        await verifier.verify_token(token)
    assert "issuer" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_verifier_invalid_audience(verifier: KeycloakJwtVerifier) -> None:
    token = create_test_jwt(
        audience="unauthorized-client-audience",
    )

    with pytest.raises(InvalidTokenError) as exc_info:
        await verifier.verify_token(token)
    assert "audience" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_verifier_invalid_signature(mock_jwk_client: MagicMock) -> None:
    other_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    # Signed with a different private key that does not match _TEST_PUBLIC_KEY
    rogue_token = create_test_jwt(private_key=other_private_key)

    verifier = KeycloakJwtVerifier(
        jwks_url="http://localhost:8080/certs",
        valid_issuers=["http://localhost:8080/realms/sports-club"],
        audience="warehouse-backend-api",
        jwk_client=mock_jwk_client,
    )

    with pytest.raises(InvalidTokenError) as exc_info:
        await verifier.verify_token(rogue_token)
    assert "validation failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_verifier_empty_token(verifier: KeycloakJwtVerifier) -> None:
    with pytest.raises(InvalidTokenError):
        await verifier.verify_token("")
