"""
Per-request LLM credential override (bring-your-own-key).

The deployed demo lets a user supply their own OpenAI-compatible API key via
request headers. We hold that key for the lifetime of a single request only,
using a contextvar — it is never written to disk, the database, or the logs.

Flow:
    middleware reads headers -> set_request_llm_override(...)
    llm_client.get_request_llm_config() merges override over settings
    middleware clears the override in a finally block

Embeddings deliberately do NOT consult this override: they always run locally
(all-MiniLM-L6-v2, 384-dim) so the FAISS index dimension stays stable whether
or not a key is present.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from backend.config import get_settings


@dataclass(frozen=True)
class LLMOverride:
    """A per-request set of OpenAI-compatible credentials."""

    api_key: str
    model: Optional[str] = None
    base_url: Optional[str] = None


# Default empty; reset per request. Never persisted.
_request_llm_override: ContextVar[Optional[LLMOverride]] = ContextVar(
    "request_llm_override", default=None
)


def set_request_llm_override(
    api_key: Optional[str],
    model: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """Set the override for the current request. Returns a reset token (or None)."""
    if not api_key or not api_key.strip():
        return None
    override = LLMOverride(
        api_key=api_key.strip(),
        model=(model.strip() if model and model.strip() else None),
        base_url=(base_url.strip() if base_url and base_url.strip() else None),
    )
    return _request_llm_override.set(override)


def clear_request_llm_override(token) -> None:
    """Reset the contextvar using the token from set_request_llm_override()."""
    if token is not None:
        _request_llm_override.reset(token)


def get_request_llm_override() -> Optional[LLMOverride]:
    """Return the current request's override, if any."""
    return _request_llm_override.get()


@dataclass(frozen=True)
class ResolvedLLMConfig:
    """Effective LLM config after merging a per-request override over settings."""

    api_key: str
    model: str
    base_url: Optional[str]
    configured: bool


def _key_looks_valid(api_key: str) -> bool:
    return bool(api_key and api_key != "sk-your-openai-api-key-here" and len(api_key) > 10)


def get_request_llm_config() -> ResolvedLLMConfig:
    """
    Resolve the LLM config for the current request.

    A per-request override (bring-your-own-key) takes precedence over the
    server-configured key. Falls back to settings; `configured` is False when
    no usable key exists (the caller then uses the mock fallback).
    """
    settings = get_settings()
    override = get_request_llm_override()

    if override is not None:
        return ResolvedLLMConfig(
            api_key=override.api_key,
            model=override.model or settings.openai_model,
            base_url=override.base_url or settings.openai_api_base,
            configured=_key_looks_valid(override.api_key),
        )

    return ResolvedLLMConfig(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_api_base,
        configured=settings.is_llm_configured,
    )
