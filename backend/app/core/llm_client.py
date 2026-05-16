"""
app/core/llm_client.py
OpenAI-compatible wrapper using Groq as the inference provider.

Fixes applied:
  - BUG: `seed=42` is not supported by all Groq models and causes API errors
    on some model endpoints. Removed it. Determinism is now achieved purely
    through temperature=0.
  - BUG: response.choices[0].message.content can be None → guard + retry
  - temperature=0 with some models returns empty content on structured prompts
    → retry at temperature=0.1 if first attempt is empty
"""

import logging
from typing import Any

from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = OpenAI(
    api_key=settings.groq_api_key,
    base_url=settings.groq_base_url,
)


def call_llm(
    *,
    system: str,
    user: str,
    max_tokens: int | None = None,
    temperature: float = 0.0,
) -> str:
    """
    Send a prompt to Groq and return the text response.

    If the model returns None / empty content at temperature=0,
    automatically retries once at temperature=0.1 before raising.

    Args:
        system:      System prompt.
        user:        User-turn content.
        max_tokens:  Token budget (defaults to llm_max_tokens_parse).
        temperature: Sampling temperature (0 = deterministic).

    Returns:
        Non-empty string response from the model.

    Raises:
        ValueError: if both attempts return empty content.
    """
    tokens = max_tokens or settings.llm_max_tokens_parse

    def _call(temp: float) -> str | None:
        logger.debug(
            "LLM call | model=%s | max_tokens=%d | temperature=%.1f",
            settings.llm_model, tokens, temp,
        )
        # FIX: Removed seed=42 — not universally supported on Groq endpoints.
        # Temperature=0 already provides near-deterministic output.
        response = _client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=tokens,
            temperature=temp,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        choice = response.choices[0]
        content = choice.message.content

        logger.debug(
            "LLM finish_reason=%s | content_len=%s",
            choice.finish_reason,
            len(content) if content else "None",
        )
        return content if content and content.strip() else None

    # First attempt: fully deterministic
    text = _call(temperature)

    if text is None:
        logger.warning(
            "LLM returned empty content at temperature=%.1f. "
            "Retrying at temperature=0.1 …", temperature,
        )
        text = _call(0.1)

    if text is None:
        raise ValueError(
            "LLM returned an empty response on both attempts. "
            "Check Groq API status or reduce prompt size."
        )

    return text


def call_llm_for_json(
    *,
    system: str,
    user: str,
    max_tokens: int | None = None,
    temperature: float = 0.0,
) -> Any:
    """Like call_llm() but auto-parses the JSON response."""
    from app.core.json_parser import parse_llm_json
    raw = call_llm(
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return parse_llm_json(raw)
