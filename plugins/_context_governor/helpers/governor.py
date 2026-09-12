from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from plugins._context_governor.helpers.artifacts import get_artifact, put_artifact
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


@dataclass(frozen=True)
class GovernorConfig:
    """Conservative defaults; tune from benchmarks rather than guessing."""

    max_chars: int = 12000
    max_visible_text_chars: int = 6000
    max_interactive_elements: int = 80
    retain_artifact: bool = True


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
    return text[:head] + "\n...[context governor: document truncated; retrieve full content explicitly]...\n" + text[-tail:]


def _extract_interactive_lines(document: Any, config: GovernorConfig) -> tuple[list[str], str]:
    """Extract stable numbered browser refs while retaining surrounding readable text."""
    text = str(document or "")
    interactive: list[str] = []
    visible_lines: list[str] = []
    ref_pattern = re.compile(r"^\s*(?:[-*]\s*)?\[(\d+)\]\s+(.+?)\s*$")
    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        match = ref_pattern.match(line)
        if match:
            if len(interactive) < max(int(config.max_interactive_elements), 0):
                interactive.append(f"[{match.group(1)}] {match.group(2)}")
            continue
        visible_lines.append(line)
    return interactive, "\n".join(visible_lines)


def browser_observation(
    browser_id: Any,
    url: Any,
    title: Any,
    document: Any = "",
    config: GovernorConfig = DEFAULT_CONFIG,
    *,
    action: str = "",
    metadata: dict[str, Any] | None = None,
    artifact_ref: str = "",
) -> str:
    """Create a compact deterministic observation for the LLM context."""
    browser_key = _clean_text(browser_id)
    clean_url = _clean_text(url)
    clean_title = _clean_text(title)
    state = BROWSER_STATE_STORE.snapshot(
        browser_id=browser_key,
        url=clean_url,
        title=clean_title,
        content=str(document or ""),
        artifact_ref=artifact_ref,
    )
    parts = [
        "BROWSER_OBSERVATION",
        f"session_id: {state.session_id}",
        f"observation_id: {state.observation_id}",
        f"browser_id: {browser_key}",
        f"sequence: {state.sequence}",
        f"changed: {str(state.changed).lower()}",
        f"url: {clean_url}",
        f"title: {clean_title}",
    ]
    if action:
        parts.append(f"action: {_clean_text(action)}")
    if state.diff and state.diff != "initial":
        parts.extend(["state_diff:", state.diff])
    if artifact_ref:
        parts.append(f"artifact_ref: {artifact_ref}")
        parts.append("artifact: full page content is retrievable explicitly")
    if metadata:
        for key, value in metadata.items():
            if key in {"document", "screenshot"}:
                continue
            if value is None or isinstance(value, (dict, list)):
                continue
            text = _clean_text(value)
            if text:
                parts.append(f"{key}: {text}")
    interactive, visible = _extract_interactive_lines(document, config)
    if interactive:
        parts.append("interactive_elements:")
        parts.extend(interactive)
    visible = visible[:max(int(config.max_visible_text_chars), 0)]
    if visible:
        parts.extend(["visible_text:", visible])
    return compact_document("\n".join(parts), config)


def _compact_document_fields(value: Any, config: GovernorConfig) -> Any:
    if isinstance(value, dict):
        return {key: compact_document(item, config) if key == "document" else _compact_document_fields(item, config) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_document_fields(item, config) for item in value]
    return value


def format_browser_result(action: str, result: Any, config: GovernorConfig = DEFAULT_CONFIG) -> str:
    """Format browser output efficiently; full `content` remains explicit."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action == "content":
        if isinstance(result, dict) and set(result.keys()) == {"document"}:
            return str(result.get("document") or "")
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if isinstance(result, dict) and "document" in result:
        document = str(result.get("document") or "")
        artifact_ref = put_artifact(document) if config.retain_artifact and document else ""
        metadata = {key: value for key, value in result.items() if key != "document"}
        browser_id = result.get("browser_id") or result.get("id")
        url = result.get("currentUrl") or result.get("url")
        title = result.get("title")
        return browser_observation(browser_id, url, title, document, config, action=normalized_action, metadata=metadata, artifact_ref=artifact_ref)
    compacted = _compact_document_fields(result, config)
    return json.dumps(compacted, indent=2, ensure_ascii=False, default=str)


def retrieve_artifact(ref: str) -> str:
    """Explicitly retrieve a previously retained full browser artifact."""
    return get_artifact(ref)


def _browser_document(result: Any) -> str:
    if isinstance(result, dict):
        document = result.get("document")
        if document is not None:
            return str(document)
        nested = result.get("result")
        if isinstance(nested, dict) and nested.get("document") is not None:
            return str(nested["document"])
    return str(result or "")


def govern_tool_result(tool_name: str, result: Any, config: GovernorConfig = DEFAULT_CONFIG) -> str:
    """Bound browser observations; leave non-browser tool results untouched."""
    if tool_name.lower() not in {"browser", "web_browser"}:
        return str(result or "")
    if isinstance(result, str) and result.startswith("BROWSER_OBSERVATION\n"):
        return result
    if isinstance(result, dict) and "document" in result:
        return format_browser_result("observation", result, config)
    return compact_document(_browser_document(result), config)
