from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost",
    "http://127.0.0.1",
)
DEFAULT_CORS_ALLOW_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM inference ────────────────────────────────────────
    aiml_api_key: str = ""
    aiml_base_url: str = "https://api.aimlapi.com/v1"
    aiml_model: str = "gpt-4o"

    # ── Market data ──────────────────────────────────────────
    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""

    # ── External intelligence sources ────────────────────────
    newsapi_key: str = ""
    reddit_enabled: bool = True
    edgar_enabled: bool = True

    # ── Infrastructure ───────────────────────────────────────
    redis_url: str = DEFAULT_REDIS_URL
    kv_url: str = ""
    public_api_base_url: str = ""
    cors_allowed_origins: str = ",".join(DEFAULT_CORS_ALLOWED_ORIGINS)
    cors_allow_origin_regex: str = DEFAULT_CORS_ALLOW_ORIGIN_REGEX

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    reload: bool = False

    # ── Security ─────────────────────────────────────────────
    api_keys: str = ""  # comma-separated valid API keys; empty = open access
    rate_limit_rpm: int = 10  # max /analyse requests per minute per IP

    # ── Pipeline feature flags ───────────────────────────────
    agent_verification: bool = True
    debate_layer: bool = True
    history_ttl_days: int = 90
    vigil_tier: str = "pro"  # "free" | "pro"

    def get_public_api_base_url(self) -> str:
        return self.public_api_base_url.strip().rstrip("/")

    def get_redis_url(self) -> str:
        raw_value = self.redis_url.strip()
        if self.kv_url.strip() and (not raw_value or raw_value == DEFAULT_REDIS_URL):
            raw_value = self.kv_url.strip()
        if raw_value and "://" not in raw_value:
            raw_value = f"redis://{raw_value}"
        return raw_value or DEFAULT_REDIS_URL

    def get_cors_allowed_origins(self) -> list[str]:
        raw_value = self.cors_allowed_origins.strip()
        if not raw_value:
            return list(DEFAULT_CORS_ALLOWED_ORIGINS)

        if raw_value.startswith("["):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                origins = [
                    str(origin).strip().rstrip("/")
                    for origin in parsed
                    if str(origin).strip()
                ]
                if origins:
                    return origins

        origins = [
            origin.strip().rstrip("/")
            for origin in raw_value.split(",")
            if origin.strip()
        ]
        return origins or list(DEFAULT_CORS_ALLOWED_ORIGINS)

    def get_cors_allow_origin_regex(self) -> str | None:
        value = self.cors_allow_origin_regex.strip()
        return value or None

    def get_api_keys(self) -> set[str]:
        raw = self.api_keys.strip()
        if not raw:
            return set()
        return {k.strip() for k in raw.split(",") if k.strip()}


settings = Settings()
