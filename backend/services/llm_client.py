"""
LLM client with async support, retry logic, response caching, and streaming.
Supports OpenAI, OpenRouter, and any OpenAI-compatible endpoint.
"""

import hashlib
import time
from collections import OrderedDict
from threading import Lock
from typing import Optional, Union, Generator

from backend.config import get_settings
from backend.services.llm_context import get_request_llm_config
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class LLMError(RuntimeError):
    """
    Raised when an LLM call fails *while a key is configured*.

    This is deliberately distinct from the keyless demo path: with no key we
    return a mock placeholder, but a configured-and-failing call (bad key,
    wrong model, unreachable base URL) must surface a real error instead of
    silently looking identical to demo mode.
    """


def _explain_llm_error(llm_config, error: Exception) -> str:
    """Build a user-facing error message, with provider-specific hints."""
    msg = str(error).strip() or error.__class__.__name__
    base = (llm_config.base_url or "").lower()
    model = llm_config.model or ""
    hints = []

    if "openrouter" in base and "/" not in model:
        hints.append(
            f"OpenRouter model names are namespaced — try 'openai/{model}' "
            f"instead of '{model}'."
        )
    if llm_config.base_url and not base.startswith(("http://", "https://")):
        hints.append(
            "The base URL should be a full URL, e.g. 'https://openrouter.ai/api/v1'."
        )

    hint_text = (" " + " ".join(hints)) if hints else ""
    return f"LLM call failed ({model}): {msg}.{hint_text}"


# ============================================
# Response Cache (LRU, thread-safe)
# ============================================

class LLMCache:
    """Thread-safe LRU cache for LLM responses."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        key = self._make_key(prompt)
        with self._lock:
            if key in self._cache:
                response, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return response
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def put(self, prompt: str, response: str) -> None:
        key = self._make_key(prompt)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (response, time.time())
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    @property
    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / max(1, self._hits + self._misses) * 100:.1f}%",
        }


# Global cache instance
_cache = LLMCache(max_size=256, ttl_seconds=3600)


# ============================================
# LLM Client
# ============================================

def get_llm_response(
    prompt: str,
    *,
    use_cache: bool = True,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    max_retries: int = 2,
) -> str:
    """
    Get a response from the LLM with caching and retry.
    
    Args:
        prompt: The prompt to send.
        use_cache: Whether to check/store in cache.
        temperature: LLM temperature.
        max_tokens: Max response tokens.
        max_retries: Number of retry attempts on failure.
    
    Returns:
        LLM response text.
    """
    llm_config = get_request_llm_config()

    if not llm_config.configured:
        logger.warning("llm_not_configured")
        return _mock_llm_response(prompt)

    # Check cache
    if use_cache:
        cached = _cache.get(prompt)
        if cached is not None:
            logger.debug("llm_cache_hit")
            return cached

    # Build LLM
    response = None
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = _call_llm(prompt, llm_config, temperature, max_tokens)
            break
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("llm_retry", attempt=attempt + 1, wait=wait, error=str(e))
                time.sleep(wait)
            else:
                logger.error("llm_call_failed", error=str(e), attempts=max_retries + 1)

    if response is None:
        # A key IS configured but the call still failed — surface a real error
        # rather than silently returning the mock placeholder (which is
        # indistinguishable from "no key configured").
        logger.error("llm_all_retries_exhausted", error=str(last_error))
        raise LLMError(_explain_llm_error(llm_config, last_error))

    # Cache successful response
    if use_cache:
        _cache.put(prompt, response)

    return response


def _call_llm(prompt: str, llm_config, temperature: float, max_tokens: int) -> str:
    """Make a single LLM API call using the resolved per-request config."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    kwargs = {
        "model": llm_config.model,
        "api_key": llm_config.api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if llm_config.base_url:
        kwargs["base_url"] = llm_config.base_url

    llm = ChatOpenAI(**kwargs)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def get_llm_streaming(prompt: str, **kwargs) -> Generator[str, None, None]:
    """
    Stream LLM response token-by-token.
    
    Yields:
        Response text chunks.
    """
    llm_config = get_request_llm_config()

    if not llm_config.configured:
        yield _mock_llm_response(prompt)
        return

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm_kwargs = {
        "model": llm_config.model,
        "api_key": llm_config.api_key,
        "temperature": kwargs.get("temperature", 0.1),
        "max_tokens": kwargs.get("max_tokens", 2000),
        "streaming": True,
    }
    if llm_config.base_url:
        llm_kwargs["base_url"] = llm_config.base_url

    llm = ChatOpenAI(**llm_kwargs)

    try:
        for chunk in llm.stream([HumanMessage(content=prompt)]):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        # Key is configured but streaming failed — surface the real error
        # instead of silently emitting the mock placeholder.
        logger.error("llm_stream_failed", error=str(e))
        yield f"⚠️ {_explain_llm_error(llm_config, e)}"


def get_cache_stats() -> dict:
    """Get LLM cache statistics."""
    return _cache.stats


# ============================================
# Mock responses (fallback)
# ============================================

def _mock_llm_response(prompt: str) -> str:
    """Generate a mock response when no LLM is configured."""
    lower = prompt.lower()

    if "summarize" in lower or "summary" in lower:
        return '{"executive_summary": "Configure an LLM API key for real summaries.", "section_summaries": [], "bullet_highlights": ["Document processed successfully", "Set OPENAI_API_KEY for AI analysis"], "key_takeaways": ["Full AI analysis requires an API key"]}'

    if "risk" in lower:
        return '{"overall_risk_score": "Unknown", "risk_items": [], "total_risks": 0}'

    if "compare" in lower or "comparison" in lower:
        return '{"summary": "Configure an LLM API key for document comparison.", "similarities": [], "differences": []}'

    if "extract" in lower:
        return '{"main_topics": ["Document processed"], "key_points": ["Set OPENAI_API_KEY for extraction"], "action_items": [], "references": []}'

    return "This is a placeholder response. Configure OPENAI_API_KEY for real AI-powered analysis."


# ============================================
# Timeout-Safe LLM Wrapper
# ============================================

import concurrent.futures
import contextvars

# Default timeout for LLM calls (seconds)
LLM_CALL_TIMEOUT = 15


def safe_llm_call(
    prompt: str,
    *,
    timeout: int = LLM_CALL_TIMEOUT,
    fallback: str = "Unable to generate a response at the moment. Please try again.",
    use_cache: bool = True,
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> str:
    """
    Timeout-safe wrapper around get_llm_response().

    Uses a thread pool to enforce a hard timeout. If the LLM call
    exceeds `timeout` seconds OR raises any exception, returns `fallback`.
    Never crashes. Never hangs.

    Args:
        prompt: The prompt to send.
        timeout: Max seconds to wait for LLM response.
        fallback: Response returned on timeout or error.
        use_cache, temperature, max_tokens: Passed through to get_llm_response().

    Returns:
        LLM response string, or fallback on failure.
    """
    # Fast path: check cache before spawning thread
    if use_cache:
        cached = _cache.get(prompt)
        if cached is not None:
            logger.debug("safe_llm_cache_hit")
            return cached

    # Copy the current context so the per-request LLM override (BYO-key) is
    # visible inside the worker thread — contextvars do not propagate to
    # ThreadPoolExecutor threads automatically.
    ctx = contextvars.copy_context()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                ctx.run,
                get_llm_response,
                prompt,
                use_cache=use_cache,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = future.result(timeout=timeout)
            return result
    except concurrent.futures.TimeoutError:
        logger.error("llm_call_timeout", timeout=timeout, prompt_preview=prompt[:80])
        return fallback
    except LLMError as e:
        # A key is configured but the call failed — surface the real reason
        # (bad key / wrong model / bad base URL) instead of the generic
        # fallback, which is indistinguishable from the keyless demo.
        logger.error("llm_call_configured_failed", error=str(e), prompt_preview=prompt[:80])
        return f"⚠️ {e}"
    except Exception as e:
        logger.error("llm_call_safe_failed", error=str(e), prompt_preview=prompt[:80])
        return fallback
