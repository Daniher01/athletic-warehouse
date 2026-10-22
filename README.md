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

### Step 2: Spin Up Infrastructure (ClickHouse, Keycloak & Backend)

Start all services (or select ones) with automated DDL initialization, seed fixtures, and realm import:

```bash
# Start all core services in background
docker compose up -d clickhouse keycloak warehouse-backend
```

Once running:
- **FastAPI OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **ClickHouse Health:** `http://localhost:8123/ping` (returns `Ok.`)
- **ClickHouse Play UI:** [http://localhost:8123/play](http://localhost:8123/play) (user: `default`, password: `clickhouse_password`, db: `athletic_warehouse`)
- **Keycloak Admin Console:** [http://localhost:8080](http://localhost:8080) (user: `admin`, password: `admin_password`)
- For complete Keycloak RBAC setup, test users, and client configuration, refer to [infra/keycloak/README.md](file:///infra/keycloak/README.md).

#### Exploring ClickHouse with GUI Tools (DbGate / DBeaver)

You can explore schemas, tables, and partitions visually using **DbGate** or **DBeaver**:
- **DbGate Connection Settings:**
  - Engine: `ClickHouse`
  - Host: `localhost`
  - Port: `8123` (HTTP) or `9000` (Native TCP)
  - User: `default`
  - Password: `clickhouse_password`
  - Database: `athletic_warehouse`
- **DBeaver Connection Settings:**
  - Driver: `ClickHouse` (Official JDBC Driver)
  - Host: `localhost` | Port: `8123`
  - Database: `athletic_warehouse` | Username: `default` | Password: `clickhouse_password`


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

### Step 3: Run the Warehouse Backend Locally (Optional for Development)

If you prefer running the backend natively outside Docker with hot-reload:

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

Send a wellness record through the Tableflow webhook endpoint (authenticated via shared webhook secret or Bearer JWT):

```bash
curl -X POST http://localhost:8000/api/v1/ingest/tableflow \
  -H "Content-Type: application/json" \
  -H "X-Tableflow-Secret: tableflow-webhook-dev-secret" \
  -d '{
    "club_id": "11111111-1111-1111-1111-111111111111",
    "department_id": "preparacion-fisica",
    "form_name": "wellness",
    "category_id": "22222222-2222-2222-2222-222222222201",
    "records": [
      {
        "player_id": "33333333-3333-3333-3333-333333333301",
        "metric_date": "2026-10-22",
        "data": {
          "rpe": 8,
          "sleep_quality": 9,
          "muscle_soreness": 3,
          "stress_level": 2,
          "fatigue_level": 4,
          "notes": "Optimal recovery after high-intensity session"
        }
      }
    ]
  }'
```

#### 2. Query Normalized Silver Data

Obtain an analyst token from Keycloak and query `fact_wellness_records`:

```bash
# Obtain Bearer token
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/sports-club/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=warehouse-backend-api" \
  -d "client_secret=backend-api-secret-123" \
  -d "username=coach_mikel" \
  -d "password=test_password_123" \
  -d "grant_type=password" | jq -r .access_token)

# Query wellness records
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/wellness?club_id=11111111-1111-1111-1111-111111111111&limit=10"
```

#### 3. Test Endpoints with Bruno

You can also test all API endpoints visually using [Bruno](https://www.usebruno.com/):
- Open Bruno -> **Open Collection** -> select `warehouse-backend/tests/bruno`.
- Run requests: `Health Check`, `Keycloak Get User Token`, `Get Auth Profile`, `Ingest Tableflow Records`, `Ingest Tableflow (Invalid)`, and `List Wellness Records`.

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
│   ├── clickhouse/
│   │   ├── init/
│   │   │   └── 01_schema.sql       # Production DDL (dimensions, bronze, silver, materialized view)
│   │   └── seeds/
│   │       └── 02_fixtures.sql     # Seed data for dev/test environments
│   └── keycloak/
│       ├── realm-export.json       # OIDC Realm export (roles, clients, groups, test users)
│       └── README.md               # Keycloak operations and token generation guide
├── warehouse-backend/
│   ├── src/warehouse_backend/
│   │   ├── domain/                 # Pure domain models & exceptions (zero external deps)
│   │   ├── application/            # Use cases & repository ports (business orchestration)
│   │   ├── infrastructure/         # Keycloak verifier, ClickHouse adapters & migrations
│   │   └── presentation/           # FastAPI routers, endpoints & schemas
│   ├── tests/                      # Unit, integration & Bruno test suites
│   └── pyproject.toml              # Dependencies & tooling configurations
└── tests/                          # Root integration & DDL tests
```
