from __future__ import annotations

import json
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
    return re.sub(r"\s+", " ", text).strip()


def compact_document(document: Any, config: GovernorConfig = DEFAULT_CONFIG) -> str:
    """Bound browser document text while preserving useful head/tail context."""
    text = str(document or "").strip()
    if not text:
        return ""
    limit = max(int(config.max_chars), 1)
    if len(text) <= limit:
        return text

    head = max(limit * 2 // 3, 1)
    tail = max(limit - head, 1)
    return (
        text[:head]
        + "\n...[context governor: document truncated; retrieve full content explicitly]...\n"
        + text[-tail:]
    )


def _compact_document_fields(value: Any, config: GovernorConfig) -> Any:
    """Compact document-bearing fields without throwing away browser metadata."""
    if isinstance(value, dict):
        return {
            key: compact_document(item, config) if key == "document" else _compact_document_fields(item, config)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_compact_document_fields(item, config) for item in value]
    return value


def format_browser_result(
    action: str,
    result: Any,
    config: GovernorConfig = DEFAULT_CONFIG,
) -> str:
    """Format browser output efficiently; full `content` remains explicit."""
    if action == "content":
        if isinstance(result, dict) and set(result.keys()) == {"document"}:
            return str(result.get("document") or "")
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    compacted = _compact_document_fields(result, config)
    return json.dumps(compacted, indent=2, ensure_ascii=False, default=str)


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
