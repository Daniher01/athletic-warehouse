from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_native_port: int = 9000
    clickhouse_db: str = "athletic_warehouse"
    clickhouse_user: str = "default"
    clickhouse_password: str = "clickhouse_password"
    api_title: str = "Athletic Warehouse Ingestion & Analytics API"
    api_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
