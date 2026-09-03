from typing import Optional, Union, List, Dict, Any
"""
Application configuration using Pydantic Settings.
Reads from .env file and environment variables.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Smart Document Insights platform."""

    # --- Application ---
    app_name: str = "Smart Document Insights"
    app_env: str = "development"
    debug: bool = True
    # Read from the SECRET_KEY env var (set an HF Space secret in production).
    # The default is an obvious sentinel so a misconfigured deploy is easy to spot.
    secret_key: str = "INSECURE-DEV-KEY-set-SECRET_KEY-env-var"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # --- OpenAI / LLM ---
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_api_base: Optional[str] = None
    llm_max_retries: int = 2
    llm_timeout: int = 60

    # --- LLM Cache ---
    llm_cache_max_size: int = 256
    llm_cache_ttl: int = 3600  # seconds

    # --- Embeddings ---
    # Local embeddings (all-MiniLM-L6-v2, 384-dim) are the default so the app
    # works with NO API key. Embeddings stay local even when an LLM key is
    # provided, to keep the FAISS index dimension stable (see embedding_service).
    embedding_model: str = "text-embedding-3-small"
    use_local_embeddings: bool = True
    embedding_cache_size: int = 512

    # --- Vector Store ---
    faiss_index_path: str = "./data/faiss_index"

    # --- Background Processing ---
    # When False (default), document processing runs inline in the request.
    # Set True only if a Celery worker + Redis broker are actually available.
    use_celery: bool = False

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- File Upload ---
    max_file_size_mb: int = 50
    upload_dir: str = "./data/uploads"
    allowed_extensions: str = "pdf,docx,txt"

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 60

    # --- CORS ---
    cors_origins: str = "*"

    # --- Feature Flags ---
    enable_multi_doc_chat: bool = True
    enable_report_generation: bool = True
    enable_highlights: bool = True

    # --- API ---
    api_version: str = "v1"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_llm_configured(self) -> bool:
        """Check if an LLM API key is configured."""
        return bool(
            self.openai_api_key
            and self.openai_api_key != "sk-your-openai-api-key-here"
            and len(self.openai_api_key) > 10
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
