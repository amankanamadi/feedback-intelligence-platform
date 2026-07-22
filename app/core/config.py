from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Customer Feedback Intelligence Platform"
    debug: bool = False
    api_port: int = 8000

    database_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Placeholder wired up in Phase 7.
    chroma_persist_dir: str = "./data/chroma"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
