# ClickHouse Dimensional Model & Schemas (Infraestructura)

Este directorio gestiona los esquemas DDL y datos semilla (*fixtures*) para el almacén analítico OLAP (ClickHouse) de Athletic Warehouse.

## Estructura de Directorios

```
infra/clickhouse/
├── init/
│   └── 01_schema.sql      # DDL de producción (esquema dimensional, bronze, silver y materialized view)
├── seeds/
│   └── 02_fixtures.sql    # Datos semilla de prueba y desarrollo (1 club, 2 categorías, 5 jugadores)
└── README.md
```

## Arquitectura de Tablas

### 1. Capa Dimensional (Star Schema)
Todas las dimensiones emplean `ENGINE = ReplacingMergeTree(updated_at)` para garantizar deduplicación determinista en merges de fondo:
- **`dim_club`**: Clave de ordenamiento `club_id`.
- **`dim_category`**: Clave de ordenamiento `(club_id, category_id)`.
- **`dim_player`**: Clave de ordenamiento `(club_id, player_id)`. Estados tipados con `Enum8('verified' = 1, 'unverified' = 2)`.

### 2. Capa Bronze (Raw Inmutable)
- **`fact_form_records_raw`**: Almacén append-only inmutable de payloads brutos en JSON (`raw_data String CODEC(ZSTD(3))`).
- **Particionado**: Mensual mediante `PARTITION BY toYYYYMM(metric_date)`.
- **Ordenamiento**: `(club_id, department_id, form_name, player_id, metric_date)`.

### 3. Capa Silver & Streaming Trigger
- **`fact_wellness_records`**: Tabla analítica fuertemente tipada con columnas normalizadas (`rpe`, `sleep_quality`, `muscle_soreness`, etc.). Motor `ReplacingMergeTree(ingested_at)` particionado por mes.
- **`mv_wellness_records`**: `MATERIALIZED VIEW` actuando como trigger atómico de inserción en streaming desde `fact_form_records_raw` filtrando por `form_name = 'wellness'` y extrayendo campos de forma tolerante a fallos (`JSONExtract(..., 'Nullable(T)')`).

## Ejecución en Desarrollo Local

Al iniciar los contenedores con Docker Compose:
```bash
docker compose up clickhouse -d
```
Los scripts de `init/` y `seeds/` se ejecutan automáticamente en orden alfabético al inicializar el volumen. En entornos de producción, únicamente se monta el directorio `init/`.
