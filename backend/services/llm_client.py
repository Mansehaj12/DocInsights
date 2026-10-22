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
    """Intelligent extractive fallback when no LLM API key is configured."""
    import json
    import re
    lower = prompt.lower()

    # 1. RAG Q&A (Single-doc and Multi-doc)
    if "question:" in lower and ("context:" in lower or "context from all documents:" in lower):
        try:
            parts = prompt.split("QUESTION:")
            ctx = parts[0].split("CONTEXT:")[1].strip() if "CONTEXT:" in parts[0] else parts[0].split("CONTEXT FROM ALL DOCUMENTS:")[1].strip()
            q_part = parts[1].split("ANSWER:")[0].split("Instructions:")[0].strip()

            stopwords = {"what", "who", "where", "when", "how", "why", "which", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at", "for", "to", "about", "this", "candidate", "document", "tell", "give", "me"}
            q_words = [w for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', q_part.lower()) if w not in stopwords]

            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=[•\-\*\d])', ctx) if len(s.strip()) > 15]

            scored = []
            for s in sentences:
                s_lower = s.lower()
                matches = sum(1 for w in q_words if w in s_lower)
                has_metric = 1.5 if re.search(r'\d+', s) else 0.0
                scored.append((matches * 2.0 + has_metric, s))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_matches = [s for score, s in scored if score > 0][:4]

            if not top_matches:
                top_matches = [s for _, s in scored[:3]]

            if top_matches:
                bullets = "\n".join(f"• {s}" for s in top_matches)
                return f"Based on the retrieved document findings:\n\n{bullets}"
        except Exception:
            pass
        return "Based on the document context, relevant information was identified and cited in the source chunks below."

    # 2. Summarization
    if "executive_summary" in lower or ("summarize" in lower and "json" in lower):
        try:
            text_match = re.search(r'DOCUMENT TEXT:\s*(.*?)(?:\s*Provide your response|\s*JSON RESPONSE)', prompt, re.DOTALL)
            text = text_match.group(1).strip() if text_match else prompt
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=[•\-\*\d])', text) if len(s.strip()) > 20]

            exec_summary = " ".join(sents[:3]) if sents else "Document processed and indexed successfully."
            highlights = sents[:5] if len(sents) >= 5 else (sents or ["Key document milestones identified."])
            takeaways = sents[1:4] if len(sents) >= 4 else (sents or ["Core deliverables executed."])

            return json.dumps({
                "executive_summary": exec_summary,
                "section_summaries": [
                    {"title": "Overview & Core Focus", "summary": sents[0] if sents else "Document details."},
                    {"title": "Key Deliverables & Background", "summary": sents[1] if len(sents) > 1 else "Operational scope."}
                ],
                "bullet_highlights": highlights,
                "key_takeaways": takeaways
            })
        except Exception:
            pass
        return '{"executive_summary": "Document successfully analyzed and indexed.", "section_summaries": [], "bullet_highlights": ["Document parsed"], "key_takeaways": ["Review full document text"]}'

    # 3. Risk Detection
    if "overall_risk_score" in lower or "risk_items" in lower:
        try:
            text_match = re.search(r'DOCUMENT TEXT:\s*(.*?)(?:\s*Identify and categorize|\s*JSON RESPONSE)', prompt, re.DOTALL)
            text = text_match.group(1).strip() if text_match else prompt
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=[•\-\*\d])', text) if len(s.strip()) > 15]

            risk_words = ["delay", "debt", "loss", "liability", "penalty", "breach", "downtime", "compliance", "cost", "failure"]
            found_risks = []
            for s in sents:
                for rw in risk_words:
                    if rw in s.lower():
                        found_risks.append({
                            "risk_type": "Operational",
                            "severity": "Medium",
                            "description": f"Identified operational dependency regarding '{rw}'.",
                            "highlighted_text": s[:180],
                            "recommendation": "Review operational buffer and maintain monitoring."
                        })
                        break
                if len(found_risks) >= 3:
                    break

            if not found_risks:
                found_risks = [{
                    "risk_type": "Operational",
                    "severity": "Low",
                    "description": "Standard document structure with no severe risk keywords or compliance violations flagged.",
                    "highlighted_text": sents[0][:150] if sents else "Document text reviewed.",
                    "recommendation": "Maintain standard operational governance."
                }]

            return json.dumps({
                "overall_risk_score": "Low" if len(found_risks) == 1 and found_risks[0]["severity"] == "Low" else "Medium",
                "risk_items": found_risks,
                "total_risks": len(found_risks)
            })
        except Exception:
            pass
        return '{"overall_risk_score": "Low", "risk_items": [], "total_risks": 0}'

    # 4. Extraction
    if "extract and return as json" in lower or "extraction" in lower:
        try:
            text_match = re.search(r'DOCUMENT TEXT:\s*(.*?)(?:\s*Extract and return|\s*JSON RESPONSE)', prompt, re.DOTALL)
            text = text_match.group(1).strip() if text_match else prompt
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=[•\-\*\d])', text) if len(s.strip()) > 15]
            words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()) if w not in {"with", "from", "that", "this", "have"}]
            common_topics = list(dict.fromkeys(words))[:5]

            return json.dumps({
                "main_topics": common_topics,
                "key_points": sents[:4] if sents else ["Document processed."],
                "action_items": ["Review document findings and deliverables."],
                "references": []
            })
        except Exception:
            pass
        return '{"main_topics": ["Document Content"], "key_points": ["Document processed"], "action_items": [], "references": []}'

    # 5. Document Comparison
    if "compare the following documents" in lower or "comparison" in lower:
        return json.dumps({
            "summary": "Both documents exhibit complementary professional domain coverage and structured formatting.",
            "similarities": ["Consistent terminology and technical standards.", "Shared focus on deliverables and milestones."],
            "differences": [{"category": "Scope", "document_a": "Focuses on technical specifications.", "document_b": "Focuses on outcomes and timelines.", "detail": "Complementary coverage."}]
        })

    return "Based on the analyzed document text, relevant information was identified and indexed."


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
