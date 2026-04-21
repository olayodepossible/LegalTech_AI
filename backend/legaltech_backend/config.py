"""Application configuration (12-factor, env-driven)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEGALTECH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LegalTech API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Data & AI layer (wire real clients in integrations/)
    database_url: str | None = None
    s3_bucket: str | None = None
    vector_collection: str = "legaltech-embeddings"
    llm_api_url: str | None = None
    llm_api_key: str | None = None

    # Queue / worker (stub URLs for production: Kafka / SQS)
    ingestion_queue_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
