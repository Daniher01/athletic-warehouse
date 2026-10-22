from pathlib import Path

from clickhouse_connect.driver.client import Client


def run_sql_script(client: Client, file_path: Path) -> None:
    """Execute all statements in an SQL script sequentially."""
    content = file_path.read_text(encoding="utf-8")
    for statement in content.split(";"):
        cleaned = statement.strip()
        if cleaned:
            client.command(cleaned)


def apply_migrations(
    client: Client,
    schema_path: Path,
    fixtures_path: Path | None = None,
) -> None:
    """Apply DDL schema migrations and optional seed fixtures."""
    if schema_path.exists():
        run_sql_script(client, schema_path)
    if fixtures_path and fixtures_path.exists():
        run_sql_script(client, fixtures_path)
