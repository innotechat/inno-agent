from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GovernorConfig:
    """Conservative defaults; tune from benchmarks rather than guessing."""

    max_chars: int = 12000
    max_visible_text_chars: int = 6000
    max_interactive_elements: int = 80


DEFAULT_CONFIG = GovernorConfig()


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_document(document: Any, config: GovernorConfig = DEFAULT_CONFIG) -> str:
    """Bound a browser document while preserving useful head/tail context."""
    text = str(document or "").strip()
    if not text:
        return ""
    if len(text) <= config.max_chars:
        return text

    head = max(config.max_chars * 2 // 3, 1)
    tail = max(config.max_chars - head, 1)
    return (
        text[:head]
        + "\n...[context governor: document truncated; retrieve full content explicitly]...\n"
        + text[-tail:]
    )


def _browser_document(result: Any) -> str:
    """Extract browser document text without stringifying the whole response object."""
    if isinstance(result, dict):
        document = result.get("document")
        if document is not None:
            return str(document)
        nested = result.get("result")
        if isinstance(nested, dict) and nested.get("document") is not None:
            return str(nested["document"])
    return str(result or "")


def browser_observation(
    browser_id: Any,
    url: Any,
    title: Any,
    document: Any = "",
    config: GovernorConfig = DEFAULT_CONFIG,
) -> str:
    """Create a compact, deterministic browser observation."""
    parts = [
        "BROWSER_OBSERVATION",
        f"browser_id: {_clean_text(browser_id)}",
        f"url: {_clean_text(url)}",
        f"title: {_clean_text(title)}",
    ]
    compact = compact_document(document, config)
    if compact:
        parts.extend(["visible_content:", compact])
    return "\n".join(parts)


def govern_tool_result(
    tool_name: str,
    result: Any,
    config: GovernorConfig = DEFAULT_CONFIG,
) -> str:
    """Bound browser observations; leave non-browser tool results untouched."""
    if tool_name.lower() not in {"browser", "web_browser"}:
        return str(result or "")
    return compact_document(_browser_document(result), config)
