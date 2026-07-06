"""
Centralized configuration for Jarvis backend.

All runtime configuration is sourced from environment variables (via .env
in development). Never hardcode secrets or environment-specific values
elsewhere in the codebase — import `settings` from this module instead.
"""
from functools import lru_cache
import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Server ---
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/jarvis.db"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 120

    # --- Weather ---
    openweather_api_key: str = ""
    default_city: str = "Lucknow"
    weather_provider: str = "openweather"

    # --- Whisper ---
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- Piper ---
    piper_binary_path: str = "piper"
    piper_voice_model_path: str = "./voices/en_US-amy-medium.onnx"
    piper_voice_config_path: str = "./voices/en_US-amy-medium.onnx.json"

    # --- Wake Word ---
    wake_word: str = "hey jarvis"
    wake_word_similarity_threshold: float = 0.72

    # --- Memory ---
    max_context_messages: int = 20

        # --- News ---
    newsdata_api_key: str = ""
    news_cache_ttl_minutes: int = 10   
    news_max_headlines: int = 5
    espn_rss_url: str = "https://www.espn.com/espn/rss/news"
    news_cache_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — avoids re-parsing env vars on every call."""
    return Settings()


settings = get_settings()
