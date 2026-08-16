"""Application configuration.

All config comes from the environment. No hardcoded values in source
(review-prompt.md: "No hardcoded config — use environment variables").
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    environment: str = "local"
    app_name: str = "BuzzCRM"


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is read once per process."""
    return Settings()
