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

    # Keycloak IAM & RBAC
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_internal_url: str = "http://localhost:8080"
    keycloak_realm: str = "sports-club"
    keycloak_audience: str = "warehouse-backend-api"
    auth_enabled: bool = True
    tableflow_webhook_secret: str = "tableflow-webhook-dev-secret"

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_base_url.rstrip('/')}/realms/{self.keycloak_realm}"

    @property
    def keycloak_internal_issuer(self) -> str:
        return f"{self.keycloak_internal_url.rstrip('/')}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        base = self.keycloak_internal_url.rstrip("/")
        return f"{base}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


settings = Settings()
