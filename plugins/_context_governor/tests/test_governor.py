from plugins._context_governor.helpers.governor import (
    GovernorConfig,
    browser_observation,
    compact_document,
    govern_tool_result,
)


def test_small_document_is_unchanged():
    value = "Hello dashboard"
    assert compact_document(value) == value


def test_large_document_is_bounded_and_marked():
    config = GovernorConfig(max_chars=100)
    result = compact_document("x" * 500, config)
    assert len(result) > 0
    assert "context governor: document truncated" in result
    assert len(result) <= 180


def test_browser_observation_contains_metadata():
    result = browser_observation(2, "https://example.test", "Dashboard", "Create post")
    assert "BROWSER_OBSERVATION" in result
    assert "browser_id: 2" in result
    assert "Create post" in result


def test_non_browser_tool_is_not_modified():
    value = "x" * 1000
    assert govern_tool_result("shell", value) == value
