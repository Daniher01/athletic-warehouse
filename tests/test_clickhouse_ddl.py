"""Integration and validation test suite for ClickHouse Medallion DDL and fixtures.

Uses embedded ClickHouse engine (chdb) to verify schema, triggers, and seed data.
"""

from pathlib import Path

import chdb


def _resolve_root() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "infra" / "clickhouse" / "init" / "01_schema.sql").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find repository root containing infra/clickhouse")


ROOT_DIR = _resolve_root()
SCHEMA_PATH = ROOT_DIR / "infra" / "clickhouse" / "init" / "01_schema.sql"
FIXTURES_PATH = ROOT_DIR / "infra" / "clickhouse" / "seeds" / "02_fixtures.sql"


def execute_sql_file(session: chdb.session.Session, file_path: Path) -> None:
    """Execute all statements in an SQL file sequentially."""
    content = file_path.read_text(encoding="utf-8")
    for statement in content.split(";"):
        cleaned = statement.strip()
        if cleaned:
            session.query(cleaned)


def test_schema_ddl_execution() -> None:
    """Verify that 01_schema.sql creates all expected database tables and views."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)

    tables_output = str(session.query("SHOW TABLES FROM athletic_warehouse"))
    expected_objects = [
        "dim_club",
        "dim_category",
        "dim_player",
        "fact_form_records_raw",
        "fact_wellness_records",
        "mv_wellness_records",
    ]
    for obj in expected_objects:
        assert obj in tables_output, f"Expected table or view '{obj}' not found in database."


def test_schema_idempotency() -> None:
    """Verify that 01_schema.sql can be executed multiple times without failure."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)
    # Re-run to ensure idempotency
    execute_sql_file(session, SCHEMA_PATH)

    tables_output = str(session.query("SHOW TABLES FROM athletic_warehouse"))
    assert "fact_wellness_records" in tables_output


def test_fixtures_seed_execution() -> None:
    """Verify that seed fixtures load 1 club, 2 categories, and 5 players."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)
    execute_sql_file(session, FIXTURES_PATH)

    # 1. Verify Club
    club_count = int(str(session.query("SELECT count() FROM athletic_warehouse.dim_club")).strip())
    assert club_count == 1
    club_name = str(session.query("SELECT name FROM athletic_warehouse.dim_club")).strip()
    assert "Athletic Club" in club_name

    # 2. Verify Categories
    cat_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.dim_category")).strip()
    )
    assert cat_count == 2

    # 3. Verify Players
    player_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.dim_player")).strip()
    )
    assert player_count == 5

    # 4. Verify Status distribution (4 verified, 1 unverified)
    verified_count = int(
        str(
            session.query(
                "SELECT count() FROM athletic_warehouse.dim_player WHERE status = 'verified'"
            )
        ).strip()
    )
    unverified_count = int(
        str(
            session.query(
                "SELECT count() FROM athletic_warehouse.dim_player WHERE status = 'unverified'"
            )
        ).strip()
    )
    assert verified_count == 4
    assert unverified_count == 1


def test_streaming_materialized_view_wellness() -> None:
    """Verify that mv_wellness_records extracts JSON fields into fact_wellness_records."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)
    execute_sql_file(session, FIXTURES_PATH)

    raw_json = (
        '{"rpe": 8, "sleep_quality": 9, "muscle_soreness": 3, '
        '"stress_level": 2, "fatigue_level": 4, "notes": "Post-match recovery"}'
    )
    raw_insert = f"""
    USE athletic_warehouse;
    INSERT INTO fact_form_records_raw (
        record_id, club_id, department_id, form_name, player_id, category_id, metric_date, raw_data
    ) VALUES (
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        '11111111-1111-1111-1111-111111111111',
        'preparacion_fisica',
        'wellness',
        '33333333-3333-3333-3333-333333333302',
        '22222222-2222-2222-2222-222222222201',
        '2026-10-22',
        '{raw_json}'
    );
    """
    for stmt in raw_insert.split(";"):
        cleaned = stmt.strip()
        if cleaned:
            session.query(cleaned)

    # Verify Bronze has 1 record
    bronze_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.fact_form_records_raw")).strip()
    )
    assert bronze_count == 1

    # Verify Silver has 1 record auto-populated via trigger
    silver_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.fact_wellness_records")).strip()
    )
    assert silver_count == 1

    # Verify column values
    query = (
        "SELECT rpe, sleep_quality, muscle_soreness, stress_level, fatigue_level, notes "
        "FROM athletic_warehouse.fact_wellness_records"
    )
    record = str(session.query(query)).strip()
    assert "8" in record
    assert "9" in record
    assert "Post-match recovery" in record


def test_streaming_mv_missing_fields_tolerance() -> None:
    """Verify that JSON records with omitted fields produce NULL without breaking."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)

    raw_insert = """
    USE athletic_warehouse;
    INSERT INTO fact_form_records_raw (
        record_id, club_id, department_id, form_name, player_id, category_id, metric_date, raw_data
    ) VALUES (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '11111111-1111-1111-1111-111111111111',
        'preparacion_fisica',
        'wellness',
        '33333333-3333-3333-3333-333333333303',
        '22222222-2222-2222-2222-222222222201',
        '2026-10-22',
        '{"rpe": 6}'
    );
    """
    for stmt in raw_insert.split(";"):
        cleaned = stmt.strip()
        if cleaned:
            session.query(cleaned)

    query = (
        "SELECT rpe, sleep_quality, notes "
        "FROM athletic_warehouse.fact_wellness_records "
        "WHERE record_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'"
    )
    silver_record = str(session.query(query)).strip()
    assert "6" in silver_record
    assert "\\N" in silver_record or "NULL" in silver_record or "null" in silver_record


def test_streaming_mv_filters_by_form_name() -> None:
    """Verify that mv_wellness_records ignores non-wellness records in Bronze."""
    session = chdb.session.Session()
    execute_sql_file(session, SCHEMA_PATH)

    raw_insert = """
    USE athletic_warehouse;
    INSERT INTO fact_form_records_raw (
        record_id, club_id, department_id, form_name, player_id, category_id, metric_date, raw_data
    ) VALUES (
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        '11111111-1111-1111-1111-111111111111',
        'preparacion_fisica',
        'gps',
        '33333333-3333-3333-3333-333333333303',
        '22222222-2222-2222-2222-222222222201',
        '2026-10-22',
        '{"total_distance": 10500, "sprints": 28}'
    );
    """
    for stmt in raw_insert.split(";"):
        cleaned = stmt.strip()
        if cleaned:
            session.query(cleaned)

    # Bronze has 1 record
    bronze_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.fact_form_records_raw")).strip()
    )
    assert bronze_count == 1

    # Silver must have 0 records because form_name != 'wellness'
    silver_count = int(
        str(session.query("SELECT count() FROM athletic_warehouse.fact_wellness_records")).strip()
    )
    assert silver_count == 0
