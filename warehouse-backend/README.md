# Athletic Warehouse Backend & Ingestion Engine

Service built with **Python 3.12+**, **FastAPI**, and **`uv`** adhering to **Clean Architecture** principles.

## Architecture

- **Domain Layer (`domain/`)**: Pure business models (`Player`, `Club`, `Category`, `FormRecord`, `WellnessRecord`) and domain exceptions. Zero external dependencies.
- **Application Layer (`application/`)**: Ingestion use cases and repository ports (`WarehouseRepositoryPort`). Enforces identity invariants and auto-provisions unverified players.
- **Infrastructure Layer (`infrastructure/`)**: ClickHouse adapters (`clickhouse-connect`), migration runner, and repository implementation.
- **Presentation Layer (`presentation/`)**: FastAPI endpoints (`/health`, `/api/v1/ingest/tableflow`, `/api/v1/wellness`).

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

## API Testing with Bruno

A pre-configured [Bruno](https://www.usebruno.com/) collection is located in `tests/bruno/`:
- `health.bru`: Check `/api/v1/health`
- `ingest-tableflow.bru`: Test POST `/api/v1/ingest/tableflow` with sample wellness payload
- `ingest-tableflow-invalid.bru`: Test validation error (HTTP 422) on missing player identity
- `list-wellness.bru`: Query GET `/api/v1/wellness` with filtering and pagination

