import pytest

from plugins._context_governor.helpers.action_safety import (
    decide_browser_action,
    guard_browser_action,
)


def test_read_only_actions_are_low_risk():
    decision = decide_browser_action({"action": "content"})
    assert decision.allowed
    assert decision.risk == "low"


def test_navigation_rejects_non_web_scheme():
    decision = decide_browser_action({"action": "navigate", "url": "javascript:alert(1)"})
    assert not decision.allowed
    assert "http" in decision.reason


def test_high_impact_requires_confirmation():
    decision = decide_browser_action({"action": "submit"})
    assert not decision.allowed
    assert decision.risk == "high"


def test_high_impact_allows_explicit_confirmation():
    decision = decide_browser_action({"action": "submit", "confirm": True})
    assert decision.allowed
    assert decision.risk == "high"


def test_payload_keyword_detection_requires_confirmation():
    decision = decide_browser_action({"action": "click", "text": "Publish post"})
    assert not decision.allowed
    assert decision.risk == "high"


def test_medium_risk_actions_remain_automatable():
    decision = decide_browser_action({"action": "click", "ref": 12})
    assert decision.allowed
    assert decision.risk == "medium"


def test_non_browser_tool_is_not_gated():
    decision = guard_browser_action("calculator", {"action": "submit"})
    assert decision.allowed
    assert decision.risk == "none"


def test_blocked_action_raises_clear_error():
    with pytest.raises(ValueError, match="requires explicit confirmation"):
        guard_browser_action("browser", {"action": "delete"})
