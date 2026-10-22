-- Athletic Warehouse - Production ClickHouse Schema DDL
-- Database initialization and Medallion Architecture Star Schema

CREATE DATABASE IF NOT EXISTS athletic_warehouse;

USE athletic_warehouse;

-- ============================================================================
-- 1. Capa Dimensional (Star Schema)
-- ============================================================================

-- Dimensión de Clubes
CREATE TABLE IF NOT EXISTS dim_club (
    club_id UUID,
    name String,
    country LowCardinality(String),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY club_id;

-- Dimensión de Categorías Deportivas
CREATE TABLE IF NOT EXISTS dim_category (
    category_id UUID,
    club_id UUID,
    name LowCardinality(String),
    sort_order UInt8,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (club_id, category_id);

-- Dimensión de Jugadores
CREATE TABLE IF NOT EXISTS dim_player (
    player_id UUID,
    club_id UUID,
    category_id UUID,
    first_name String,
    last_name String,
    nationality LowCardinality(String),
    birth_date Date,
    position LowCardinality(String),
    status Enum8('verified' = 1, 'unverified' = 2),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (club_id, player_id);

-- ============================================================================
-- 2. Capa Bronze (Raw Inmutable)
-- ============================================================================

-- Buzón universal inmutable para todas las cargas de formularios
CREATE TABLE IF NOT EXISTS fact_form_records_raw (
    record_id UUID,
    club_id UUID,
    department_id LowCardinality(String),
    form_name LowCardinality(String),
    player_id UUID,
    category_id UUID,
    metric_date Date,
    ingested_at DateTime DEFAULT now(),
    raw_data String CODEC(ZSTD(3))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(metric_date)
ORDER BY (club_id, department_id, form_name, player_id, metric_date);

-- ============================================================================
-- 3. Capa Silver (Tablas Analíticas Fuertemente Tipadas)
-- ============================================================================

-- Registros normalizados del formulario de Wellness
CREATE TABLE IF NOT EXISTS fact_wellness_records (
    record_id UUID,
    club_id UUID,
    player_id UUID,
    category_id UUID,
    metric_date Date,
    rpe Nullable(UInt8),
    sleep_quality Nullable(UInt8),
    muscle_soreness Nullable(UInt8),
    stress_level Nullable(UInt8),
    fatigue_level Nullable(UInt8),
    notes Nullable(String),
    ingested_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(metric_date)
ORDER BY (club_id, metric_date, player_id);

-- ============================================================================
-- 4. Streaming Trigger (Materialized View)
-- ============================================================================

-- Transformación continua en tiempo real desde Bronze a Silver
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_wellness_records TO fact_wellness_records AS
SELECT
    record_id,
    club_id,
    player_id,
    category_id,
    metric_date,
    JSONExtract(raw_data, 'rpe', 'Nullable(UInt8)') AS rpe,
    JSONExtract(raw_data, 'sleep_quality', 'Nullable(UInt8)') AS sleep_quality,
    JSONExtract(raw_data, 'muscle_soreness', 'Nullable(UInt8)') AS muscle_soreness,
    JSONExtract(raw_data, 'stress_level', 'Nullable(UInt8)') AS stress_level,
    JSONExtract(raw_data, 'fatigue_level', 'Nullable(UInt8)') AS fatigue_level,
    JSONExtract(raw_data, 'notes', 'Nullable(String)') AS notes,
    ingested_at
FROM fact_form_records_raw
WHERE form_name = 'wellness';
