"""Thin async wrapper around the OpenAI-compatible inference endpoint.

Every agent calls `llm_complete` with its XML-tagged system prompt and a
user message.  The function returns the raw assistant content string.
"""

from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from vigil.core.config import settings

logger = logging.getLogger("vigil.llm")

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.aiml_api_key,
            base_url=settings.aiml_base_url,
        )
    return _client


async def llm_complete(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    client = _get_client()
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


async def llm_json(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict:
    """Call LLM and parse the response as JSON.

    Attempts to extract a JSON object even if the model wraps it in
    markdown fences.
    """
    raw = await llm_complete(
        system_prompt, user_message,
        temperature=temperature, max_tokens=max_tokens,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(cleaned[start:end])
        raise
