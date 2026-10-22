import clickhouse_connect
from clickhouse_connect.driver.client import Client

from warehouse_backend.config import Settings


def create_clickhouse_client(settings: Settings) -> Client:
    """Create a ClickHouse client connection instance."""
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )
