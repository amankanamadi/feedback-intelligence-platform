from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Customer Feedback Intelligence Platform"
    debug: bool = False
    api_port: int = 8000

    database_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2

    # Cosine distance beyond which a "similar" match is excluded as
    # irrelevant - 1.0 is the point where cosine similarity turns
    # non-positive (no genuine semantic relationship).
    rag_max_distance: float = 1.0
    rag_query_timeout_ms: int = 2000

    # Defends against an oversized upload before row-parsing even happens.
    bulk_upload_max_file_bytes: int = 2_000_000

    # Relative by default so local dev "just works"; docker-compose.yml
    # overrides this to an absolute path backed by a named volume.
    attachments_dir: str = "./attachments"
    attachment_max_size_bytes: int = 5_000_000
    attachment_max_files_per_upload: int = 5

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
