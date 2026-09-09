from plugins._context_governor.helpers.governor import (
    GovernorConfig,
    browser_observation,
    compact_document,
    format_browser_result,
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


def test_browser_dict_extracts_document_only():
    result = govern_tool_result(
        "browser",
        {"document": "Create post", "screenshot": "large-reference", "metadata": "keep-out"},
    )
    assert result == "Create post"
    assert "screenshot" not in result
    assert "metadata" not in result


def test_browser_result_preserves_metadata_while_compacting_document():
    config = GovernorConfig(max_chars=80)
    result = format_browser_result(
        "click",
        {"document": "x" * 500, "browser_id": 2, "url": "https://example.test"},
        config,
    )
    assert "browser_id" in result
    assert "https://example.test" in result
    assert "context governor: document truncated" in result
    assert len(result) < 700


def test_content_action_remains_explicit_full_retrieval():
    value = "x" * 500
    result = format_browser_result("content", {"document": value})
    assert result == value


def test_non_browser_tool_is_not_modified():
    value = "x" * 1000
    assert govern_tool_result("shell", value) == value
