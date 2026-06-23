"""Application settings, loaded from environment (12-factor — ADR-003)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values come from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CF_", extra="ignore")

    # Service
    environment: str = "dev"
    service_name: str = "contestforge-api"
    log_level: str = "INFO"

    # Datastores
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contestforge"
    redis_url: str = "redis://localhost:6379/0"
    db_pool_min: int = 10
    db_pool_max: int = 100

    # Auth
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1209600  # 14 days

    # Multi-tenancy
    enforce_query_scoping: bool = True  # rejects unscoped tenant queries (technical-spec §7.1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
