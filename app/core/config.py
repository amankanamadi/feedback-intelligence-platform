from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Airbnb Guest Experience Intelligence Platform"
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

    # Much tighter than rag_max_distance: this is "is this the same
    # complaint" (near-identical text), not "is this loosely related".
    duplicate_detection_max_distance: float = 0.15

    # Defends against an oversized upload before row-parsing even happens.
    bulk_upload_max_file_bytes: int = 2_000_000

    # Relative by default so local dev "just works"; docker-compose.yml
    # overrides this to an absolute path backed by a named volume.
    attachments_dir: str = "./attachments"
    attachment_max_size_bytes: int = 5_000_000
    attachment_max_files_per_upload: int = 5

    # Safety cap on export size, not a real limit at current data scale.
    feedback_export_max_rows: int = 10_000

    # Auth - JWT secret must be set via .env in any non-debug deployment;
    # get_settings() below fails loudly rather than booting with a blank
    # secret that would make every token forgeable.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_minutes: int = 10_080  # 7 days
    password_reset_token_expire_minutes: int = 30

    # False for local http dev; set True in prod so cookies require HTTPS.
    cookie_secure: bool = False
    cookie_domain: Optional[str] = None

    # Explicit allowlist - CORSMiddleware rejects "*" when
    # allow_credentials=True is needed for cookie-based auth.
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.debug and not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be set when DEBUG is false.")
    return settings
