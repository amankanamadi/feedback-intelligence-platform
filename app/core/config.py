from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Customer Feedback Intelligence Platform"
    debug: bool = False
    api_port: int = 8000

    # Placeholders wired up by later phases.
    database_url: str = ""
    openai_api_key: str = ""
    chroma_persist_dir: str = "./data/chroma"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
