"""
Centralised configuration via pydantic-settings.
Values are read from environment variables or a .env file in the backend directory.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All runtime settings for FireReach backend.
    Set these in your .env file (see .env.example).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: Literal["gemini", "groq"] = "gemini"
    """Which LLM provider to use: 'gemini' (Google) or 'groq' (Llama 3)."""

    gemini_api_key: str = ""
    """Google Gemini API key (required when llm_provider='gemini')."""

    groq_api_key: str = ""
    """Groq API key (required when llm_provider='groq')."""

    gemini_model: str = "gemini-3-flash-preview"
    groq_model: str = "llama3-70b-8192"

    # ── Tavily ────────────────────────────────────────────────────────────────
    tavily_api_key: str = ""
    """Tavily Search API key for live signal harvesting."""

    # ── SMTP (email sending) ───────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    """Sender email address (e.g. yourname@gmail.com)."""
    smtp_password: str = ""
    """App-password or SMTP password for the sender account."""
    smtp_from_name: str = "FireReach"

    # ── App ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once at startup)."""
    return Settings()
