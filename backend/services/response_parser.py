"""
Robust JSON response parser for LLM outputs.
Handles markdown fences, trailing commas, partial JSON, and other common LLM quirks.
"""

import json
import re
from typing import Optional, Union, Any

from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


def parse_json_response(response: str, default: Optional[dict] = None) -> dict:
    """
    Parse a JSON response from an LLM, handling common formatting issues:
    - Markdown code fences (```json ... ```)
    - Trailing commas before ] or }
    - Extra text before/after JSON
    - Nested JSON strings
    
    Args:
        response: Raw LLM response string.
        default: Fallback dict if parsing fails entirely.
    
    Returns:
        Parsed dictionary.
    """
    if not response or not response.strip():
        return default or {"raw_response": ""}

    cleaned = response.strip()

    # Step 1: Strip markdown code fences
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Step 2: Try direct parse
    result = _try_parse(cleaned)
    if result is not None:
        return result

    # Step 3: Fix trailing commas and retry
    fixed = _fix_trailing_commas(cleaned)
    result = _try_parse(fixed)
    if result is not None:
        return result

    # Step 4: Extract outermost { ... } block
    brace_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if brace_match:
        extracted = brace_match.group()
        result = _try_parse(extracted)
        if result is not None:
            return result

        fixed = _fix_trailing_commas(extracted)
        result = _try_parse(fixed)
        if result is not None:
            return result

    # Step 5: Try to extract [ ... ] array
    array_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if array_match:
        result = _try_parse(array_match.group())
        if result is not None:
            return {"items": result} if isinstance(result, list) else result

    logger.warning("json_parse_failed", response_preview=cleaned[:200])
    return default or {"raw_response": response}


def validate_summary_response(data: dict) -> dict:
    """Ensure summary response has all required keys."""
    return {
        "executive_summary": data.get("executive_summary", ""),
        "section_summaries": data.get("section_summaries", []),
        "bullet_highlights": data.get("bullet_highlights", []),
        "key_takeaways": data.get("key_takeaways", []),
    }


def validate_risk_response(data: dict) -> dict:
    """Ensure risk response has all required keys."""
    return {
        "overall_risk_score": data.get("overall_risk_score", "Medium"),
        "risk_items": data.get("risk_items", []),
        "total_risks": data.get("total_risks", len(data.get("risk_items", []))),
    }


def validate_comparison_response(data: dict) -> dict:
    """Ensure comparison response has all required keys."""
    return {
        "summary": data.get("summary", ""),
        "similarities": data.get("similarities", []),
        "differences": data.get("differences", []),
    }


# ============================================
# Internal helpers
# ============================================

def _try_parse(text: str) -> Optional[Union[dict, list]]:
    """Attempt JSON parse, return None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before ] or }."""
    return re.sub(r',\s*([}\]])', r'\1', text)
