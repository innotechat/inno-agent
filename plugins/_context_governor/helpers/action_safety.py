from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


READ_ONLY_ACTIONS = {
    "list",
    "state",
    "content",
    "detail",
    "screenshot",
    "scroll",
    "hover",
}

EDIT_ACTIONS = {
    "type",
    "select_option",
    "set_checked",
    "upload_file",
    "clipboard",
    "copy",
    "cut",
    "paste",
}

NAVIGATION_ACTIONS = {"open", "navigate", "back", "forward", "reload", "set_active", "activate", "focus"}

HIGH_IMPACT_ACTIONS = {
    "submit",
    "type_submit",
    "publish",
    "send",
    "delete",
    "remove",
    "purchase",
    "buy",
    "checkout",
    "confirm",
    "pay",
    "security_change",
    "change_password",
    "change_email",
    "grant_access",
    "revoke_access",
}

IRREVERSIBLE_KEYWORDS = {
    "publish",
    "post",
    "send",
    "delete",
    "remove",
    "purchase",
    "buy",
    "checkout",
    "pay",
    "transfer",
    "submit",
    "confirm",
    "grant",
    "revoke",
}


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    risk: str
    reason: str


def _normalized_action(action: Any) -> str:
    return str(action or "state").strip().lower().replace("-", "_")


def _confirmed(args: dict[str, Any]) -> bool:
    value = args.get("confirm")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "approved", "confirm"}


def _looks_high_impact(args: dict[str, Any]) -> bool:
    action = _normalized_action(args.get("action"))
    if action in HIGH_IMPACT_ACTIONS:
        return True
    for key in ("text", "url", "selector", "event_type"):
        value = str(args.get(key) or "").lower()
        if any(word in value for word in IRREVERSIBLE_KEYWORDS):
            return True
    return False


def _is_external_http_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in {"http", "https"}
    except ValueError:
        return False


def decide_browser_action(args: dict[str, Any] | None) -> ActionDecision:
    args = args or {}
    action = _normalized_action(args.get("action"))

    if _looks_high_impact(args):
        if _confirmed(args):
            return ActionDecision(True, "high", "explicit confirmation supplied")
        return ActionDecision(
            False,
            "high",
            "high-impact browser action requires explicit confirmation; use confirm=true only after reviewing the target and intended effect",
        )

    if action in READ_ONLY_ACTIONS:
        return ActionDecision(True, "low", "read-only browser action")

    if action in NAVIGATION_ACTIONS:
        url = str(args.get("url") or "").strip()
        if action in {"open", "navigate"} and url and not _is_external_http_url(url):
            return ActionDecision(False, "medium", "navigation target must use http or https")
        return ActionDecision(True, "low", "navigation is reversible")

    if action in EDIT_ACTIONS or action in {"click", "double_click", "right_click", "drag", "wheel", "keyboard", "key_chord", "mouse", "set_viewport", "evaluate"}:
        return ActionDecision(True, "medium", "action is allowed with target/precondition validation")

    if action in {"close", "close_all"}:
        return ActionDecision(True, "medium", "browser lifecycle action")

    return ActionDecision(True, "medium", "unknown browser action remains allowed; runtime validation is authoritative")


def guard_browser_action(tool_name: str, args: dict[str, Any] | None) -> ActionDecision:
    if str(tool_name or "").lower() not in {"browser", "web_browser"}:
        return ActionDecision(True, "none", "non-browser tool")
    decision = decide_browser_action(args)
    if not decision.allowed:
        raise ValueError(f"Browser action blocked: {decision.reason}")
    return decision
