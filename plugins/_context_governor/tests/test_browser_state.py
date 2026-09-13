from __future__ import annotations

import time

import pytest

from plugins._context_governor.helpers.artifacts import ARTIFACT_STORE, put_artifact
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE, BrowserStateStore
from plugins._context_governor.helpers.governor import browser_observation
from plugins._context_governor.tools.browser_artifact import BrowserArtifact
from plugins._context_governor.tools.browser_state import BrowserState


@pytest.fixture(autouse=True)
def clear_state():
    BROWSER_STATE_STORE.clear()
    ARTIFACT_STORE.clear()
    yield
    BROWSER_STATE_STORE.clear()
    ARTIFACT_STORE.clear()


def _observation_id(observation: str) -> str:
    return next(line.split(": ", 1)[1] for line in observation.splitlines() if line.startswith("observation_id:"))


def _tool(tool_type):
    return object.__new__(tool_type)


def test_snapshot_has_stable_session_and_unique_observation_ids():
    first = browser_observation(7, "https://example.test", "Home", "[12] Create\nWelcome")
    second = browser_observation(7, "https://example.test", "Home", "[12] Create\nWelcome")
    assert "session_id: bsess_" in first
    assert "changed: true" in first
    assert "changed: false" in second
    assert "sequence: 2" in second
    assert first != second


def test_unchanged_page_does_not_repeat_large_visible_context():
    document = "[12] Create post\n" + "important page text " * 500
    first = browser_observation(7, "https://example.test", "Home", document)
    second = browser_observation(7, "https://example.test", "Home", document)
    assert "visible_text:" in first
    assert "important page text" not in second
    assert "interactive_elements:" not in second
    assert "state: unchanged" in second
    assert len(second) < len(first) / 3


def test_state_diff_detects_added_and_removed_lines():
    browser_observation(3, "https://example.test", "A", "[1] Old\nhello")
    second = browser_observation(3, "https://example.test", "B", "[2] New\nhello")
    assert "state_diff:" in second
    assert "+ [2] New" in second
    assert "- [1] Old" in second


def test_browser_ids_are_isolated():
    first = browser_observation(1, "https://a.test", "A", "one")
    second = browser_observation(2, "https://b.test", "B", "two")
    assert "sequence: 1" in first
    assert "sequence: 1" in second
    assert "changed: true" in second
    assert BROWSER_STATE_STORE.latest(1).session_id != BROWSER_STATE_STORE.latest(2).session_id


def test_close_invalidates_latest_state():
    observation = browser_observation(5, "https://example.test", "Home", "hello")
    observation_id = _observation_id(observation)
    BROWSER_STATE_STORE.close(5)
    assert BROWSER_STATE_STORE.latest(5) is None
    with pytest.raises(KeyError):
        BROWSER_STATE_STORE.get(observation_id)


def test_ttl_expires_observations(monkeypatch):
    store = BrowserStateStore(ttl_seconds=1)
    snapshot = store.snapshot(browser_id=9, url="u", title="t", content="c")
    monkeypatch.setattr(time, "time", lambda: snapshot.created_at + 2)
    assert store.latest(9) is None
    with pytest.raises(KeyError):
        store.get(snapshot.observation_id)


def test_snapshot_eviction_removes_latest_only_when_evicted():
    store = BrowserStateStore(max_snapshots=2)
    first = store.snapshot(browser_id=1, url="u1", title="t", content="1")
    second = store.snapshot(browser_id=2, url="u2", title="t", content="2")
    third = store.snapshot(browser_id=3, url="u3", title="t", content="3")
    with pytest.raises(KeyError):
        store.get(first.observation_id)
    assert store.latest(2) is second
    assert store.latest(3) is third


@pytest.mark.asyncio
async def test_browser_state_tool_returns_latest_and_diff():
    observation = browser_observation(4, "https://example.test", "Home", "hello")
    observation_id = _observation_id(observation)
    latest = await _tool(BrowserState).execute(browser_id="4")
    diff = await _tool(BrowserState).execute(observation_id=observation_id, mode="diff")
    assert "BROWSER_STATE" in latest.message
    assert "BROWSER_STATE_DIFF" in diff.message
    assert observation_id in diff.message


@pytest.mark.asyncio
async def test_browser_artifact_targeted_query_returns_context():
    ref = put_artifact("Title\nCreate post\nPost body\nNotifications\nSearch")
    result = await _tool(BrowserArtifact).execute(ref=ref, query="post", context_lines=1)
    assert "Create post" in result.message
    assert "Post body" in result.message


@pytest.mark.asyncio
async def test_browser_artifact_element_ref_returns_target_and_context():
    ref = put_artifact("Header\n[12] Create post\nPost body\nFooter")
    result = await _tool(BrowserArtifact).execute(ref=ref, element_ref="12", context_lines=1)
    assert "[12] Create post" in result.message
    assert "Post body" in result.message
    assert "Footer" not in result.message


@pytest.mark.asyncio
async def test_browser_artifact_line_region_is_bounded():
    ref = put_artifact("one\ntwo\nthree\nfour")
    result = await _tool(BrowserArtifact).execute(ref=ref, start_line=2, end_line=3)
    assert result.message == "two\nthree"


@pytest.mark.asyncio
async def test_browser_artifact_unknown_ref_is_safe():
    result = await _tool(BrowserArtifact).execute(ref="browser://missing")
    assert "unknown or expired" in result.message


def test_artifact_ref_survives_observation_budget():
    document = "\n".join(f"[1{i}] element {i}" for i in range(1, 1000))
    observation = browser_observation(8, "https://example.test", "Large", document)
    assert "artifact_ref: browser://" in observation
