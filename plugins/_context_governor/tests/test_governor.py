from plugins._context_governor.helpers.artifacts import ArtifactStore
from plugins._context_governor.helpers.governor import (
    GovernorConfig,
    browser_observation,
    compact_browser_metadata,
    compact_document,
    format_browser_result,
    govern_tool_result,
)
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


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
    document = "\n".join(["[1] One", "[2] Two", "[3] Three", "Visible text that is deliberately long"])
    result = browser_observation(1, "https://example.test", "Test", document, config)
    assert "[1] One" in result
    assert "[2] Two" in result
    assert "[3] Three" not in result
    assert "Visible text that i" in result


def test_browser_result_preserves_metadata_and_structures_document():
    result = format_browser_result(
        "click",
        {"document": "Dashboard\n[12] Create post\nRecent activity", "browser_id": 2, "url": "https://example.test", "success": True},
    )
    assert "BROWSER_OBSERVATION" in result
    assert "browser_id: 2" in result
    assert "https://example.test" in result
    assert "action: click" in result
    assert "[12] Create post" in result
    assert "success: True" in result
    assert "artifact_ref: browser://" in result


def test_browser_result_redacts_sensitive_metadata():
    result = format_browser_result(
        "click",
        {
            "document": "Dashboard",
            "browser_id": 2,
            "url": "https://example.test",
            "success": True,
            "password": "super-secret",
            "access_token": "token-value",
            "cookie": "session-cookie",
            "api_key": "api-secret",
            "authorization": "Bearer secret",
        },
    )
    assert "super-secret" not in result
    assert "token-value" not in result
    assert "session-cookie" not in result
    assert "api-secret" not in result
    assert "Bearer secret" not in result
    assert "success: True" in result


def test_prompt_metadata_does_not_create_or_advance_browser_state():
    assert BROWSER_STATE_STORE.latest(99) is None
    result = compact_browser_metadata(99, "https://example.test", "Dashboard")
    assert "browser_id: 99" in result
    assert "state_tracking: browser tool observations only" in result
    assert BROWSER_STATE_STORE.latest(99) is None


def test_close_action_invalidates_requested_browser_state():
    browser_observation(2, "https://example.test", "Dashboard", "hello")
    result = format_browser_result("close", {"success": True}, browser_id=2)
    assert '"success": true' in result
    assert BROWSER_STATE_STORE.latest(2) is None


def test_close_action_reconciles_removed_browser_from_runtime_listing():
    browser_observation(1, "https://one.test", "One", "one")
    browser_observation(2, "https://two.test", "Two", "two")
    result = format_browser_result(
        "close",
        {
            "browsers": [{"id": 1, "currentUrl": "https://one.test", "title": "One"}],
            "last_interacted_browser_id": 1,
        },
    )
    assert "browsers" in result
    assert BROWSER_STATE_STORE.latest(1) is not None
    assert BROWSER_STATE_STORE.latest(2) is None


def test_artifact_store_retrieves_and_expires_safely():
    store = ArtifactStore(ttl_seconds=1, max_artifacts=2, max_chars=100)
    ref = store.put("FULL DOCUMENT")
    assert ref.startswith("browser://")
    assert store.get(ref) == "FULL DOCUMENT"
    try:
        store.get("browser://not-valid")
        assert False, "invalid artifact reference must fail"
    except KeyError:
        pass


def test_artifact_store_bounds_capacity():
    store = ArtifactStore(max_artifacts=1)
    first = store.put("first")
    second = store.put("second")
    assert store.get(second) == "second"
    try:
        store.get(first)
        assert False, "oldest artifact should be evicted"
    except KeyError:
        pass


def test_content_action_remains_explicit_full_retrieval():
    value = "x" * 500
    result = format_browser_result("content", {"document": value})
    assert result == value


def test_non_browser_tool_is_not_modified():
    value = "x" * 1000
    assert govern_tool_result("shell", value) == value
