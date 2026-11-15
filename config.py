"""
config.py — Centralised application configuration.

Loads all settings from environment variables (via python-dotenv).
Provides a single Config object that every other module imports.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (parent of this file's directory)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)


class Config:
    """Central configuration container loaded from environment variables."""

    # ------------------------------------------------------------------ #
    # LLM Provider & API Configuration
    # ------------------------------------------------------------------ #
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()  # "groq" or "openai"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Base URL for OpenAI-compatible providers (Groq: https://api.groq.com/openai/v1)
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

    # Models (Defaults suited for Groq or OpenAI)
    GENERATOR_MODEL: str = os.getenv("GENERATOR_MODEL", "openai/gpt-oss-20b")
    EVALUATOR_MODEL: str = os.getenv("EVALUATOR_MODEL", "openai/gpt-oss-20b")
    GENERATOR_TEMPERATURE: float = float(os.getenv("GENERATOR_TEMPERATURE", "0.7"))
    EVALUATOR_TEMPERATURE: float = float(os.getenv("EVALUATOR_TEMPERATURE", "0.1"))

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = os.getenv("APP_NAME", "AI Lesson Studio")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))

    # ------------------------------------------------------------------ #
    # Database & Filesystem
    # ------------------------------------------------------------------ #
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/lesson_generator.db")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ------------------------------------------------------------------ #
    # Mock mode (no API key required)
    # ------------------------------------------------------------------ #
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() == "true"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def get_active_api_key(cls) -> str:
        """Return the active API key depending on provider."""
        if cls.LLM_PROVIDER == "groq":
            return cls.GROQ_API_KEY or cls.OPENAI_API_KEY
        return cls.OPENAI_API_KEY

    @classmethod
    def get_active_base_url(cls) -> str | None:
        """Return base URL if using Groq or custom provider."""
        if cls.OPENAI_BASE_URL:
            return cls.OPENAI_BASE_URL
        if cls.LLM_PROVIDER == "groq":
            return "https://api.groq.com/openai/v1"
        return None

    @classmethod
    def is_api_key_configured(cls) -> bool:
        """Return True when a valid API key is present for the active provider."""
        key = cls.get_active_api_key()
        placeholder_keys = {"your_openai_api_key_here", "your_groq_api_key_here", ""}
        return bool(key and key not in placeholder_keys)

    @classmethod
    def effective_mock_mode(cls) -> bool:
        """Return True when MOCK_MODE is set OR no API key is available."""
        return cls.MOCK_MODE or not cls.is_api_key_configured()

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create required filesystem directories if they do not exist."""
        Path(cls.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


# Module-level singleton
config = Config()
