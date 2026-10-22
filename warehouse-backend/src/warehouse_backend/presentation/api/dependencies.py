from functools import lru_cache
from typing import Annotated

from clickhouse_connect.driver.client import Client
from fastapi import Depends

from warehouse_backend.application.ports.warehouse_repository import WarehouseRepositoryPort
from warehouse_backend.application.use_cases.get_wellness_metrics import GetWellnessMetricsUseCase
from warehouse_backend.application.use_cases.ingest_records import IngestTableflowRecordsUseCase
from warehouse_backend.config import Settings, settings
from warehouse_backend.infrastructure.clickhouse.client import create_clickhouse_client
from warehouse_backend.infrastructure.clickhouse.repository import ClickHouseWarehouseRepository


@lru_cache
def get_settings() -> Settings:
    return settings


@lru_cache
def get_clickhouse_client_dependency() -> Client:
    return create_clickhouse_client(get_settings())


def get_warehouse_repository(
    client: Annotated[Client, Depends(get_clickhouse_client_dependency)],
) -> WarehouseRepositoryPort:
    return ClickHouseWarehouseRepository(client)


def get_ingest_use_case(
    repo: Annotated[WarehouseRepositoryPort, Depends(get_warehouse_repository)],
) -> IngestTableflowRecordsUseCase:
    return IngestTableflowRecordsUseCase(repo)


def get_wellness_metrics_use_case(
    repo: Annotated[WarehouseRepositoryPort, Depends(get_warehouse_repository)],
) -> GetWellnessMetricsUseCase:
    return GetWellnessMetricsUseCase(repo)
