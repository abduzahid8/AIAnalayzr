"""Async LLM client with retry, structured output, and token estimation.

Every agent calls `llm_complete` or `llm_json`.  All calls go through a
single OpenAI-compatible endpoint configured via AIML_API_KEY / AIML_BASE_URL.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import AsyncOpenAI, APITimeoutError, RateLimitError, APIConnectionError

from vigil.core.config import settings

logger = logging.getLogger("vigil.llm")

_client: AsyncOpenAI | None = None
_startup_warned = False

RETRIABLE_EXCEPTIONS = (APITimeoutError, RateLimitError, APIConnectionError, TimeoutError)
DEFAULT_MAX_RETRIES = 3
CHARS_PER_TOKEN_ESTIMATE = 4


def _get_client() -> AsyncOpenAI:
    global _client, _startup_warned
    if _client is None:
        if not settings.aiml_api_key:
            if not _startup_warned:
                logger.error(
                    "AIML_API_KEY is not set — LLM calls will fail. "
                    "Set it in .env or environment variables."
                )
                _startup_warned = True
            raise RuntimeError("LLM API key (AIML_API_KEY) is not configured")
        _client = AsyncOpenAI(
            api_key=settings.aiml_api_key,
            base_url=settings.aiml_base_url,
            timeout=120.0,
        )
    return _client


def estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ~ 4 chars). Use for budget checks, not billing."""
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within an approximate token budget."""
    max_chars = max_tokens * CHARS_PER_TOKEN_ESTIMATE
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    logger.warning(
        "Truncated LLM input from ~%d to ~%d tokens",
        estimate_tokens(text), max_tokens,
    )
    return truncated + "\n\n[... truncated to fit context window ...]"


async def llm_complete(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> str:
    """Call LLM with automatic retry on transient failures."""
    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=settings.aiml_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content or ""
            logger.debug("LLM response length: %d chars", len(content))
            return content

        except RETRIABLE_EXCEPTIONS as exc:
            if attempt >= max_retries:
                logger.error("LLM call failed after %d retries: %s", max_retries, exc)
                raise
            wait = min(2 ** attempt + 0.5, 10.0)
            logger.warning(
                "LLM retry %d/%d after %s (%.1fs backoff)",
                attempt + 1, max_retries, type(exc).__name__, wait,
            )
            await asyncio.sleep(wait)

    raise RuntimeError("LLM call exhausted all retries")


async def llm_json(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict:
    """Call LLM and parse response as JSON dict.

    Uses response_format when supported, falls back to extraction.
    """
    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=settings.aiml_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or ""
            parsed = _extract_json_dict(raw)
            if parsed is not None:
                return parsed
            raise ValueError(f"JSON parse failed on response: {raw[:200]}")

        except RETRIABLE_EXCEPTIONS as exc:
            if attempt >= max_retries:
                logger.error("LLM JSON call failed after %d retries: %s", max_retries, exc)
                raise
            wait = min(2 ** attempt + 0.5, 10.0)
            logger.warning(
                "LLM JSON retry %d/%d after %s (%.1fs backoff)",
                attempt + 1, max_retries, type(exc).__name__, wait,
            )
            await asyncio.sleep(wait)

        except (ValueError, json.JSONDecodeError) as exc:
            if attempt >= max_retries:
                raise
            logger.warning("LLM JSON parse retry %d/%d: %s", attempt + 1, max_retries, exc)
            await asyncio.sleep(1.0)

    raise RuntimeError("LLM JSON call exhausted all retries")


async def llm_json_fallback(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict:
    """Fallback JSON extraction for models that don't support response_format."""
    raw = await llm_complete(
        system_prompt, user_message,
        temperature=temperature, max_tokens=max_tokens,
    )
    parsed = _extract_json_dict(raw)
    if parsed is not None:
        return parsed
    raise ValueError(f"Could not extract valid JSON dict from LLM response: {raw[:200]}")


def _extract_json_dict(text: str) -> dict | None:
    """Extract a JSON dict from text, handling markdown fences and array wrappers."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    parsed = _try_parse_json(cleaned)
    if parsed is not None:
        return _ensure_dict(parsed)

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        parsed = _try_parse_json(cleaned[start:end])
        if parsed is not None:
            return _ensure_dict(parsed)

    return None


def _try_parse_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _ensure_dict(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
        return value[0]
    return None
