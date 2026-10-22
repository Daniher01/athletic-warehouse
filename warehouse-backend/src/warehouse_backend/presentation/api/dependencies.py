import hmac
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from clickhouse_connect.driver.client import Client
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from warehouse_backend.application.auth.interfaces import TokenVerifierPort
from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.application.use_cases.get_wellness_metrics import GetWellnessMetricsUseCase
from warehouse_backend.application.use_cases.ingest_records import IngestTableflowRecordsUseCase
from warehouse_backend.config import Settings, settings
from warehouse_backend.domain.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from warehouse_backend.domain.auth.models import AuthenticatedUser, DepartmentRole
from warehouse_backend.infrastructure.auth.hmac_verifier import verify_tableflow_hmac_signature
from warehouse_backend.infrastructure.auth.keycloak_verifier import KeycloakJwtVerifier
from warehouse_backend.infrastructure.clickhouse.client import create_clickhouse_client
from warehouse_backend.infrastructure.clickhouse.repository import ClickHouseWarehouseRepository

http_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_settings() -> Settings:
    return settings


@lru_cache
def get_token_verifier() -> TokenVerifierPort:
    current_settings = get_settings()
    return KeycloakJwtVerifier(
        jwks_url=current_settings.keycloak_jwks_url,
        valid_issuers=[
            current_settings.keycloak_issuer,
            current_settings.keycloak_internal_issuer,
        ],
        audience=current_settings.keycloak_audience,
    )


@lru_cache
def get_clickhouse_client_dependency() -> Client:
    return create_clickhouse_client(get_settings())


def get_warehouse_repository(
    client: Annotated[Client, Depends(get_clickhouse_client_dependency)],
) -> WarehouseRepositoryPort:
    return ClickHouseWarehouseRepository(client)


def get_ingest_use_case(
    repo: Annotated[WarehouseRepositoryPort, Depends(get_warehouse_repository)],
) -> IngestTableflowRecordsUseCase:
    return IngestTableflowRecordsUseCase(repo)


def get_wellness_metrics_use_case(
    repo: Annotated[WarehouseRepositoryPort, Depends(get_warehouse_repository)],
) -> GetWellnessMetricsUseCase:
    return GetWellnessMetricsUseCase(repo)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer_scheme)],
    verifier: Annotated[TokenVerifierPort, Depends(get_token_verifier)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Security dependency that verifies Bearer JWT token against Keycloak JWKS."""
    if not app_settings.auth_enabled:
        # Fallback only when explicitly disabled in settings
        return AuthenticatedUser(
            user_id="dev-bypass-user",
            username="dev_admin",
            roles=frozenset({"dept_admin", "dept_ingestor", "dept_analyst"}),
            groups=("/Departamentos/Direccion-Deportiva",),
            departments=frozenset({"direccion-deportiva", "medico", "preparacion-fisica"}),
        )

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await verifier.verify_token(credentials.credentials)
    except TokenExpiredError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def require_role(
    *required_roles: str | DepartmentRole,
) -> Callable[..., AuthenticatedUser]:
    """Dependency factory enforcing one or more RBAC roles."""
    expected_values = {r.value if isinstance(r, DepartmentRole) else str(r) for r in required_roles}

    def role_checker(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.is_admin():
            return user

        if not any(user.has_role(r) for r in expected_values):
            role_names = sorted(list(expected_values))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient permissions. Required role: {role_names}",
            )
        return user

    return role_checker


def check_department_access(user: AuthenticatedUser, department_id: str) -> None:
    """Validate that the authenticated user is allowed to access the specified department."""
    if not user.can_access_department(department_id):
        msg = (
            f"Forbidden: User '{user.username}' is not authorized for department '{department_id}'."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg,
        )


async def verify_tableflow_webhook_auth(
    request: Request,
    app_settings: Annotated[Settings, Depends(get_settings)],
    verifier: Annotated[TokenVerifierPort, Depends(get_token_verifier)],
    x_tableflow_signature: Annotated[str | None, Header(alias="X-Tableflow-Signature")] = None,
    x_tableflow_secret: Annotated[str | None, Header(alias="X-Tableflow-Secret")] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer_scheme)] = None,
) -> AuthenticatedUser | None:
    """Authenticate Tableflow webhook via HMAC-SHA256, shared secret, or Bearer JWT token."""
    if not app_settings.auth_enabled:
        return None

    # 1. Check cryptographic HMAC-SHA256 signature over raw body
    if x_tableflow_signature is not None:
        raw_body = await request.body()
        if verify_tableflow_hmac_signature(
            raw_body=raw_body,
            secret=app_settings.tableflow_webhook_secret,
            signature_header=x_tableflow_signature,
        ):
            return None  # Authenticated as verified cryptographic webhook
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid 'X-Tableflow-Signature' HMAC-SHA256 digest.",
        )

    # 2. Fallback to shared secret header with constant-time comparison
    if x_tableflow_secret is not None:
        if hmac.compare_digest(x_tableflow_secret, app_settings.tableflow_webhook_secret):
            return None  # Authenticated via shared secret
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid 'X-Tableflow-Secret' header.",
        )

    # 3. Check Bearer token (Keycloak OIDC)
    if credentials and credentials.credentials:
        try:
            user = await verifier.verify_token(credentials.credentials)
            if not user.has_role(DepartmentRole.INGESTOR) and not user.is_admin():
                msg = "Forbidden: Webhook ingestion requires 'dept_ingestor' or 'dept_admin' role."
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=msg,
                )
            return user
        except (TokenExpiredError, InvalidTokenError) as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid webhook authorization token: {str(err)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from err

    # 4. Neither signature, secret, nor token provided
    msg = (
        "Unauthorized: Tableflow webhook requires a valid 'X-Tableflow-Signature' header, "
        "'X-Tableflow-Secret' header, or Bearer JWT token."
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=msg,
        headers={"WWW-Authenticate": "Bearer"},
    )
