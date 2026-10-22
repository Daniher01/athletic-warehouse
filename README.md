# Athletic Warehouse

> Enterprise sports analytics platform and high-performance columnar data warehouse for professional football clubs.

Athletic Warehouse coordinates data ingestion, schema validation, identity invariants, and real-time analytical transformations across physical preparation, medical, and tactical departments.

---

## Architecture Overview

```
                                  ┌───────────────────────────┐
                                  │   Tableflow / CSV / XLSX  │
                                  └─────────────┬─────────────┘
                                                │ (Webhook)
                                                ▼
┌─────────────────────────┐       ┌───────────────────────────┐
│     Keycloak OIDC       │◀─────▶│     warehouse-backend     │
│ (RBAC / JWT Validation) │       │   (FastAPI / Clean Arch)  │
└─────────────────────────┘       └─────────────┬─────────────┘
                                                │ (Ingest Raw)
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │              ClickHouse OLAP                  │
                        │                                               │
                        │  ┌─────────────────────────────────────────┐  │
                        │  │ 1. Capa Dimensional (ReplacingMergeTree) │  │
                        │  │    dim_club, dim_category, dim_player   │  │
                        │  └─────────────────────────────────────────┘  │
                        │                       │                       │
                        │  ┌────────────────────▼────────────────────┐  │
                        │  │ 2. Capa Bronze (fact_form_records_raw)  │  │
                        │  │    Immutable monthly-partitioned JSON   │  │
                        │  └────────────────────┬────────────────────┘  │
                        │                       │ (Streaming Trigger)   │
                        │                       ▼ (mv_wellness_records) │
                        │  ┌─────────────────────────────────────────┐  │
                        │  │ 3. Capa Silver (fact_wellness_records)  │  │
                        │  │    Typed analytical tabular models      │  │
                        │  └────────────────────┬────────────────────┘  │
                        └───────────────────────┼───────────────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │       Metabase BI         │
                                  │  (Dashboards & Reporting) │
                                  └───────────────────────────┘
```

---

## Quickstart & Local Setup

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose (or Podman)
- [uv](https://docs.astral.sh/uv/) (Python package manager, Python 3.12+)

---

### Step 1: Clone & Pull Latest Code

```bash
git clone https://github.com/Daniher01/athletic-warehouse.git
cd athletic-warehouse
git pull origin main
```

---

### Step 2: Spin Up Infrastructure (ClickHouse)

Start the ClickHouse columnar engine with automated DDL initialization and seed fixtures:

```bash
docker compose up -d clickhouse
```

Once running, verify ClickHouse health:
- **Ping Endpoint:** `http://localhost:8123/ping` (returns `Ok.`)
- **Web Query Interface (Play):** [http://localhost:8123/play](http://localhost:8123/play)
  - Default User: `default`
  - Default Password: `clickhouse_password`
  - Database: `athletic_warehouse`

To inspect the tables directly from the command line:

```bash
docker compose exec clickhouse clickhouse-client \
  --user default \
  --password clickhouse_password \
  --database athletic_warehouse \
  --query "
    SELECT 'dim_club' as table_name, count() as total FROM dim_club
    UNION ALL
    SELECT 'dim_category', count() FROM dim_category
    UNION ALL
    SELECT 'dim_player', count() FROM dim_player;
  "
```

*Expected output: 1 club, 2 categories, 5 players seeded.*

---

### Step 3: Run the Warehouse Backend

Navigate to `warehouse-backend/` and start the FastAPI service:

```bash
cd warehouse-backend
uv sync
uv run uvicorn warehouse_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started:
- **Interactive OpenAPI Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Service Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) (validates backend + ClickHouse connectivity)

---

### Step 4: Test Streaming Transformation (Bronze ➔ Silver)

#### 1. Ingest Raw Tableflow Form Payload

Send a wellness record through the Tableflow webhook endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/ingest/tableflow \
  -H "Content-Type: application/json" \
  -d '{
    "club_id": "11111111-1111-1111-1111-111111111111",
    "department_id": "preparacion_fisica",
    "form_name": "wellness",
    "records": [
      {
        "player_id": "33333333-3333-3333-3333-333333333301",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "metric_date": "2026-10-22",
        "rpe": 8,
        "sleep_quality": 9,
        "muscle_soreness": 3,
        "stress_level": 2,
        "fatigue_level": 4,
        "notes": "Optimal recovery after high-intensity session"
      }
    ]
  }'
```

#### 2. Query Normalized Silver Data

Verify the streaming Materialized View extracted and typed the record into `fact_wellness_records`:

```bash
curl "http://localhost:8000/api/v1/wellness?club_id=11111111-1111-1111-1111-111111111111&metric_date=2026-10-22"
```

---

## Automated Verification & Test Suites

### Root Level Tests (Embedded ClickHouse DDL)
Run ClickHouse schema verification tests using embedded `chdb`:

```bash
uv run pytest
```

### Warehouse Backend Verification
Run test suites, linting, formatting checks, and strict type verification:

```bash
cd warehouse-backend
uv run ruff check
uv run ruff format --check
uv run mypy .
uv run pytest
```

---

## Directory Structure

```
athletic-warehouse/
├── docker-compose.yml              # Local container stack (ClickHouse, Keycloak, Metabase, Tableflow)
├── infra/
│   └── clickhouse/
│       ├── init/
│       │   └── 01_schema.sql       # Production DDL (dimensions, bronze, silver, materialized view)
│       └── seeds/
│           └── 02_fixtures.sql     # Seed data for dev/test environments
├── warehouse-backend/
│   ├── src/warehouse_backend/
│   │   ├── domain/                 # Pure domain models & exceptions (zero external deps)
│   │   ├── application/            # Use cases & repository ports (business orchestration)
│   │   ├── infrastructure/         # ClickHouse adapters & migration runner
│   │   └── presentation/           # FastAPI routers, endpoints & schemas
│   ├── tests/                      # Unit & integration test suites
│   └── pyproject.toml              # Dependencies & tooling configurations
└── tests/                          # Root integration & DDL tests
```
