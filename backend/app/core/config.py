"""
app/core/config.py
Central settings — loaded from .env via pydantic-settings.
Import `settings` everywhere; never call os.getenv() directly.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Groq / OpenAI-compatible API
    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # FIX: "openai/gpt-oss-20b" does NOT exist on Groq.
    # Use a real Groq-hosted model. llama-3.3-70b-versatile is the flagship.
    # Other valid options: "llama3-70b-8192", "mixtral-8x7b-32768", "llama3-8b-8192"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_max_tokens_parse: int = 1500
    llm_max_tokens_expand: int = 3000

    # Storage
    upload_dir: str = "uploads"

    # Graph propagation
    propagation_decay: float = 0.6
    propagation_max_depth: int = 3

    # Scoring thresholds
    match_threshold: float = 1.0   # coverage >= this → "matched"
    infer_threshold: float = 0.1   # coverage >= this → "inferred"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
