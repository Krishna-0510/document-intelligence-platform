"""
Application configuration.

Code-quality rule (mandatory):
'API keys, credentials and tokens must be read from environment variables.'

Nothing in this file is a real secret. Values are read from the environment
(via a .env file locally, or platform env vars in deployment) using
pydantic-settings, which fails loudly if you try to hardcode instead.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "Document Intelligence Platform"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # --- Database ---
    # Default is local SQLite for the 3-day build; override via env var in
    # deployment (e.g. postgresql://user:pass@host:5432/dbname).
    database_url: str = "sqlite:///./document_intelligence.db"

    # --- LLM / Extraction provider ---
    # Never hardcode the key itself — only its *name* lives in code.
    llm_provider: str = "openai"  # openai | gemini | anthropic | ...
    llm_api_key: str = ""         # populated from env at runtime
    llm_model: str = "gpt-4o-mini"

    # --- OCR ---
    ocr_engine: str = "tesseract"  # tesseract | ocr_space | google_vision
    ocr_api_key: str = ""          # only used if a hosted OCR provider is selected

    # --- Upload constraints (from the spec) ---
    max_pages: int = 3
    allowed_mime_types: tuple[str, ...] = (
        "application/pdf",
        "image/jpeg",
        "image/png",
    )

    # --- Logging ---
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read env once, reuse everywhere."""
    return Settings()
