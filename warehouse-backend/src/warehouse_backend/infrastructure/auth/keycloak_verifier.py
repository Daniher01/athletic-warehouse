import logging
from typing import Any

import jwt
from jwt import PyJWKClient, PyJWKClientError
from jwt.types import Options

from warehouse_backend.application.auth.interfaces import TokenVerifierPort
from warehouse_backend.domain.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from warehouse_backend.domain.auth.models import AuthenticatedUser

logger = logging.getLogger(__name__)


class KeycloakJwtVerifier(TokenVerifierPort):
    """Infrastructure adapter that verifies Keycloak OIDC JWT tokens via JWKS (RS256)."""

    def __init__(
        self,
        jwks_url: str,
        valid_issuers: list[str],
        audience: str | None = None,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self.jwks_url = jwks_url
        self.valid_issuers = [iss.rstrip("/") for iss in valid_issuers if iss]
        self.audience = audience
        self.jwk_client = jwk_client or PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Validate signature, claims, expiry, issuer and return AuthenticatedUser."""
        if not token or not token.strip():
            raise InvalidTokenError("Authentication token is missing or empty.")

        try:
            # 1. Retrieve signing key matching token's kid
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)

            # 2. Decode unverified header/claims to determine issuer
            unverified_options: Options = {
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            }
            unverified_claims = jwt.decode(
                token,
                options=unverified_options,
            )
            token_issuer = unverified_claims.get("iss", "").rstrip("/")

            if self.valid_issuers and token_issuer not in self.valid_issuers:
                raise InvalidTokenError(
                    f"Invalid token issuer: '{token_issuer}'. Expected one of {self.valid_issuers}"
                )

            verification_options: Options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                # Custom audience check below to support multiple client formats
                "verify_aud": False,
            }
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=token_issuer,
                options=verification_options,
            )

            # 4. Audience validation if configured
            if self.audience:
                token_aud = payload.get("aud")
                audiences: list[str] = (
                    token_aud
                    if isinstance(token_aud, list)
                    else [token_aud]
                    if isinstance(token_aud, str)
                    else []
                )
                # Allow if configured audience is present or if token is generated for known clients
                if self.audience not in audiences and "account" not in audiences:
                    # If direct client_id matches audience
                    token_azp = payload.get("azp")
                    if token_azp != self.audience:
                        raise InvalidTokenError(
                            f"Invalid token audience: {audiences}. Expected '{self.audience}'."
                        )

            return self._build_authenticated_user(payload)

        except (TokenExpiredError, InvalidTokenError):
            raise
        except jwt.ExpiredSignatureError as err:
            raise TokenExpiredError("Authentication token has expired.") from err
        except (jwt.PyJWTError, PyJWKClientError) as err:
            logger.warning("Token verification failed: %s", str(err))
            raise InvalidTokenError(f"Token validation failed: {str(err)}") from err
        except Exception as err:
            logger.error("Unexpected error validating token: %s", str(err))
            raise InvalidTokenError(f"Unexpected error validating token: {str(err)}") from err

    def _build_authenticated_user(self, payload: dict[str, Any]) -> AuthenticatedUser:
        """Extract roles, groups, and department mappings from verified JWT claims."""
        user_id = str(payload.get("sub") or "")
        username = str(payload.get("preferred_username") or payload.get("clientId") or user_id)
        email = payload.get("email")

        # Extract roles from realm_access and resource_access
        extracted_roles: set[str] = set()
        realm_access = payload.get("realm_access") or {}
        if isinstance(realm_access, dict):
            for role in realm_access.get("roles", []):
                if isinstance(role, str):
                    extracted_roles.add(role)

        resource_access = payload.get("resource_access") or {}
        if isinstance(resource_access, dict):
            for client_data in resource_access.values():
                if isinstance(client_data, dict):
                    for role in client_data.get("roles", []):
                        if isinstance(role, str):
                            extracted_roles.add(role)

        # Extract groups and map departments
        raw_groups = payload.get("groups") or []
        groups_list: list[str] = [g for g in raw_groups if isinstance(g, str)]

        extracted_departments: set[str] = set()
        for group in groups_list:
            # Expected pattern: /Departamentos/<DepartmentName>
            # or /<Club>/Departamentos/<DepartmentName>
            parts = [
                p.strip().lower().replace("_", "-")
                for p in group.strip("/").split("/")
                if p.strip()
            ]
            if "departamentos" in parts:
                dept_idx = parts.index("departamentos") + 1
                if dept_idx < len(parts):
                    extracted_departments.add(parts[dept_idx])
            elif parts:
                # Fallback to direct group leaf
                extracted_departments.add(parts[-1])

        # Explicit department_id claim support
        explicit_dept = payload.get("department_id")
        if explicit_dept and isinstance(explicit_dept, str):
            extracted_departments.add(explicit_dept.strip().lower().replace("_", "-"))

        return AuthenticatedUser(
            user_id=user_id,
            username=username,
            email=str(email) if email else None,
            roles=frozenset(extracted_roles),
            groups=tuple(groups_list),
            departments=frozenset(extracted_departments),
        )
