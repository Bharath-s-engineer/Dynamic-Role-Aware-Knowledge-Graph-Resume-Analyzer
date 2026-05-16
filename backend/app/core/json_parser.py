"""
app/core/json_parser.py
Robust JSON extraction from LLM output.

Handles:
  - Markdown fences  ```json ... ```
  - Preamble text before JSON
  - Trailing commentary after JSON
  - Truncated responses (incomplete JSON due to max_tokens cutoff)
"""

import json
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _strip_fences(text: str) -> str:
    m = _FENCE.search(text)
    return m.group(1).strip() if m else text


def _extract_first_object(text: str) -> str:
    """Walk the string and pull out the first complete JSON object/array."""
    start = depth = None
    opener = closer = None
    for i, ch in enumerate(text):
        if start is None:
            if ch == "{":
                start, depth, opener, closer = i, 1, "{", "}"
            elif ch == "[":
                start, depth, opener, closer = i, 1, "[", "]"
        else:
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return text


def _try_recover_truncated(raw: str) -> Any | None:
    """
    If the model response was cut off mid-JSON (max_tokens hit),
    try to salvage whatever complete objects exist inside it.

    Strategy: find all complete {...} objects at the top level of an array
    and wrap them into a valid list or dict.
    """
    # Find the start of the JSON structure
    start = -1
    for i, ch in enumerate(raw):
        if ch in ("{", "["):
            start = i
            break
    if start == -1:
        return None

    opener = raw[start]

    if opener == "{":
        # Truncated object — try to find complete key:value pairs
        # Collect all complete nested objects
        objects = []
        depth = 0
        obj_start = None
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                if depth == 1:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 1 and obj_start is not None:
                    try:
                        obj = json.loads(raw[obj_start:i + 1])
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
        if objects:
            logger.warning(
                "Recovered %d object(s) from truncated LLM response. "
                "Consider raising max_tokens or reducing prompt size.",
                len(objects),
            )
            return objects
        return None

    elif opener == "[":
        # Truncated array — collect complete items
        items = []
        depth = 0
        item_start = None
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                if depth == 1:
                    item_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 1 and item_start is not None:
                    try:
                        item = json.loads(raw[item_start:i + 1])
                        items.append(item)
                    except json.JSONDecodeError:
                        pass
                    item_start = None
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
        if items:
            logger.warning(
                "Recovered %d object(s) from truncated LLM response. "
                "Consider raising max_tokens or reducing prompt size.",
                len(items),
            )
            return items
        return None

    return None


def parse_llm_json(raw: str) -> Any:
    """
    Parse JSON from an LLM response string.

    Attempts in order:
      1. Strip markdown fences → json.loads
      2. Extract first bracket-balanced object → json.loads
      3. Raw json.loads
      4. Truncation recovery (salvage partial response)

    Raises:
        ValueError: if all strategies fail.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response.")

    candidates = [
        _strip_fences(raw).strip(),
        _extract_first_object(raw).strip(),
        raw.strip(),
    ]

    for attempt in candidates:
        if not attempt:
            continue
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue

    # Last resort: recover from truncated output
    recovered = _try_recover_truncated(raw)
    if recovered is not None:
        return recovered

    preview = raw[:300].replace("\n", " ")
    logger.error("JSON parse failed after all strategies. Preview: %s", preview)
    raise ValueError(
        f"Could not extract valid JSON from LLM output. Preview: {preview!r}"
    )
