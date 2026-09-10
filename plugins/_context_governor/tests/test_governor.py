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


def test_browser_observation_extracts_interactive_refs():
    document = """
    Dashboard
    [12] Create post
    [17] Search
    [23] Notifications
    Recent activity
    """
    result = browser_observation(2, "https://example.test", "Dashboard", document)
    assert "interactive_elements:" in result
    assert "[12] Create post" in result
    assert "[17] Search" in result
    assert "[23] Notifications" in result
    assert "visible_text:" in result
    assert "Dashboard" in result
    assert "Recent activity" in result


def test_browser_observation_bounds_interactive_elements_and_visible_text():
    config = GovernorConfig(max_visible_text_chars=20, max_interactive_elements=2)
    document = "\n".join(
        ["[1] One", "[2] Two", "[3] Three", "Visible text that is deliberately long"]
    )
    result = browser_observation(1, "https://example.test", "Test", document, config)
    assert "[1] One" in result
    assert "[2] Two" in result
    assert "[3] Three" not in result
    assert "Visible text that i" in result


def test_browser_result_preserves_metadata_and_structures_document():
    result = format_browser_result(
        "click",
        {
            "document": "Dashboard\n[12] Create post\nRecent activity",
            "browser_id": 2,
            "url": "https://example.test",
            "success": True,
        },
    )
    assert "BROWSER_OBSERVATION" in result
    assert "browser_id: 2" in result
    assert "https://example.test" in result
    assert "action: click" in result
    assert "[12] Create post" in result
    assert "success: True" in result


def test_content_action_remains_explicit_full_retrieval():
    value = "x" * 500
    result = format_browser_result("content", {"document": value})
    assert result == value


def test_non_browser_tool_is_not_modified():
    value = "x" * 1000
    assert govern_tool_result("shell", value) == value
