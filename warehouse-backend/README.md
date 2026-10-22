# Athletic Warehouse Backend & Ingestion Engine

Service built with **Python 3.12+**, **FastAPI**, and **`uv`** adhering to **Clean Architecture** principles.

## Architecture

- **Domain Layer (`domain/`)**: Pure business models (`Player`, `Club`, `Category`, `FormRecord`, `WellnessRecord`, `AuthenticatedUser`, `DepartmentRole`), deterministic natural key slug algorithm (`[initials]-[DDMMYYYY]`), deterministic UUIDv5 player mapping, and domain exceptions. Zero external dependencies.
- **Application Layer (`application/`)**: Ingestion use cases (`IngestTableflowRecordsUseCase`), authentication ports (`TokenVerifierPort`), and repository ports (`WarehouseRepositoryPort`). Enforces identity invariants, RBAC policies, and batch auto-provisions unverified players into the OLAP store.
- **Infrastructure Layer (`infrastructure/`)**: Keycloak RS256 JWKS JWT verifier, HMAC-SHA256 webhook cryptographic signature verifier (`TableflowHmacVerifier`), ClickHouse batch adapters (`clickhouse-connect`), migration runner, and repository implementation.
- **Presentation Layer (`presentation/`)**: FastAPI endpoints (`/health`, `/api/v1/auth/me`, `/api/v1/ingest/tableflow`, `/api/v1/wellness`) and RBAC security dependencies (`get_current_user`, `require_role`, `check_department_access`, `verify_tableflow_webhook_auth`).

## Verification Commands

Run from `warehouse-backend/`:

```bash
# Tests
uv run pytest

# Linter and Formatter
uv run ruff check
uv run ruff format --check

# Type Checker
uv run mypy .
```

## Running the Service

### Option A: Via Docker Compose (Recommended)

From the project root:

```bash
# Start backend alongside ClickHouse and Keycloak
docker compose up -d clickhouse keycloak warehouse-backend
```

### Option B: Local Development with `uv`

```bash
cd warehouse-backend
uv sync
uv run uvicorn warehouse_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Testing with Bruno

A pre-configured [Bruno](https://www.usebruno.com/) collection is located in `tests/bruno/`:
- `health.bru`: Check `/api/v1/health` (no authentication required)
- `keycloak-token.bru`: Request user access token from Keycloak OIDC password grant
- `auth-me.bru`: Test GET `/api/v1/auth/me` to inspect verified token claims and departments
- `ingest-tableflow.bru`: Test POST `/api/v1/ingest/tableflow` with sample wellness payload (`X-Tableflow-Secret`)
- `ingest-tableflow-invalid.bru`: Test validation error (HTTP 422) on missing player identity
- `list-wellness.bru`: Query GET `/api/v1/wellness` with filtering and pagination (requires `dept_analyst` / `dept_admin`)

