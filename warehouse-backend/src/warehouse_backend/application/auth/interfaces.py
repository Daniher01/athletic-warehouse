from typing import Protocol

from warehouse_backend.domain.auth.models import AuthenticatedUser


class TokenVerifierPort(Protocol):
    """Port for verifying authentication tokens and returning authenticated user domain models."""

    async def verify_token(self, token: str) -> AuthenticatedUser: ...
