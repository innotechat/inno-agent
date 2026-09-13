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
_SENSITIVE_METADATA_PATTERN = re.compile(
    r"(?:^|[_-])(password|passwd|secret|token|cookie|authorization|credential|api[_-]?key|access[_-]?key|refresh[_-]?token)(?:$|[_-])",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    text = str(value or "")
    return re.sub(r"\s+", " ", text).strip()


def _is_sensitive_metadata_key(key: Any) -> bool:
    normalized = str(key or "").strip()
    return bool(_SENSITIVE_METADATA_PATTERN.search(normalized))


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
    marker = "\n...[context governor: document truncated; retrieve full content explicitly]...\n"
    return (text[:head] + marker + text[-tail:])[:limit]


def compact_browser_metadata(browser_id: Any, url: Any, title: Any, config: GovernorConfig = DEFAULT_CONFIG) -> str:
    """Serialize browser metadata without mutating the state store."""
    parts = [
        "BROWSER_OBSERVATION",
        f"browser_id: {_clean_text(browser_id)}",
        f"url: {_clean_text(url)}",
        f"title: {_clean_text(title)}",
        "state_tracking: browser tool observations only",
    ]
    return compact_document("\n".join(parts), config)


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


def _compact_observation(parts: list[str], config: GovernorConfig) -> str:
    """Compact observation payload while preserving critical identity/recovery fields."""
    limit = max(int(config.max_chars), 1)
    text = "\n".join(parts)
    if len(text) <= limit:
        return text

    payload_start = next((i for i, item in enumerate(parts) if item == "__PAYLOAD__"), None)
    if payload_start is None:
        return compact_document(text, config)

    header = "\n".join(parts[:payload_start])
    payload = "\n".join(parts[payload_start + 1:])
    if len(header) >= limit:
        priority = [
            line for line in parts[:payload_start]
            if line.startswith((
                "BROWSER_OBSERVATION",
                "session_id:",
                "observation_id:",
                "browser_id:",
                "artifact_ref:",
            ))
        ]
        return "\n".join(priority)[:limit]

    remaining = limit - len(header) - 1
    if remaining <= 0:
        return header[:limit]
    payload_config = GovernorConfig(
        max_chars=remaining,
        max_visible_text_chars=config.max_visible_text_chars,
        max_interactive_elements=config.max_interactive_elements,
        retain_artifact=config.retain_artifact,
    )
    return header + "\n" + compact_document(payload, payload_config)


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
    if artifact_ref:
        parts.append(f"artifact_ref: {artifact_ref}")
        parts.append("artifact: full page content is retrievable explicitly")
    if action:
        parts.append(f"action: {_clean_text(action)}")
    if state.diff and state.diff != "initial" and state.changed:
        parts.extend(["state_diff:", state.diff])

    if not state.changed:
        parts.append("state: unchanged; use browser_artifact for targeted retrieval if needed")
    else:
        if metadata:
            for key, value in metadata.items():
                if key in {"document", "screenshot"} or _is_sensitive_metadata_key(key):
                    continue
                if value is None or isinstance(value, (dict, list)):
                    continue
                text = _clean_text(value)
                if text:
                    parts.append(f"{key}: {text}")
        interactive, visible = _extract_interactive_lines(document, config)
        payload = ["__PAYLOAD__"]
        if interactive:
            payload.append("interactive_elements:")
            payload.extend(interactive)
        visible = visible[:max(int(config.max_visible_text_chars), 0)]
        if visible:
            payload.extend(["visible_text:", visible])
        parts.extend(payload)
    return _compact_observation(parts, config)


def _compact_document_fields(value: Any, config: GovernorConfig) -> Any:
    if isinstance(value, dict):
        return {key: compact_document(item, config) if key == "document" else _compact_document_fields(item, config) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_document_fields(item, config) for item in value]
    return value


def _browser_id_from_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return None
    state = result.get("state") if isinstance(result.get("state"), dict) else {}
    browsers = result.get("browsers") if isinstance(result.get("browsers"), list) else []
    last_id = result.get("last_interacted_browser_id")
    if last_id is not None:
        return last_id
    return result.get("browser_id") or result.get("id") or state.get("id") or next(
        (browser.get("id") for browser in browsers if isinstance(browser, dict) and browser.get("id") is not None),
        None,
    )


def _closed_browser_ids_from_result(result: Any) -> tuple[str, ...]:
    """Infer browser ids removed by a close result when the tool does not pass the requested id."""
    if not isinstance(result, dict):
        return ()
    browsers = result.get("browsers")
    if not isinstance(browsers, list):
        return ()
    remaining = {
        str(browser.get("id"))
        for browser in browsers
        if isinstance(browser, dict) and browser.get("id") is not None
    }
    return tuple(browser_id for browser_id in BROWSER_STATE_STORE.browser_ids() if browser_id not in remaining)


def format_browser_result(
    action: str,
    result: Any,
    config: GovernorConfig = DEFAULT_CONFIG,
    *,
    browser_id: Any = None,
) -> str:
    """Format browser output efficiently; full `content` remains explicit."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action == "content":
        if isinstance(result, dict) and set(result.keys()) == {"document"}:
            return str(result.get("document") or "")
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    if normalized_action in {"close", "close_all"}:
        if normalized_action == "close_all":
            BROWSER_STATE_STORE.clear()
        else:
            resolved_browser_id = browser_id
            if resolved_browser_id is not None:
                BROWSER_STATE_STORE.close(resolved_browser_id)
            else:
                for closed_id in _closed_browser_ids_from_result(result):
                    BROWSER_STATE_STORE.close(closed_id)
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    if isinstance(result, dict) and "document" in result:
        document = str(result.get("document") or "")
        artifact_ref = put_artifact(document) if config.retain_artifact and document else ""
        metadata = {key: value for key, value in result.items() if key != "document"}
        resolved_browser_id = result.get("browser_id") or result.get("id") or browser_id
        url = result.get("currentUrl") or result.get("url")
        title = result.get("title")
        return browser_observation(resolved_browser_id, url, title, document, config, action=normalized_action, metadata=metadata, artifact_ref=artifact_ref)
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
