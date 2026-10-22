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
