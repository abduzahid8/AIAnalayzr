from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aiml_api_key: str = ""
    aiml_base_url: str = "https://api.aimlapi.com/v1"
    aiml_model: str = "gpt-4o"

    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


settings = Settings()
