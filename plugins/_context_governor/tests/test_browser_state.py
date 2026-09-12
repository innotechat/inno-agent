from __future__ import annotations

import pytest

from plugins._context_governor.helpers.artifacts import ARTIFACT_STORE, put_artifact
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE
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


def test_snapshot_has_stable_session_and_unique_observation_ids():
    first = browser_observation(7, "https://example.test", "Home", "[12] Create\nWelcome")
    second = browser_observation(7, "https://example.test", "Home", "[12] Create\nWelcome")
    assert "session_id: bsess_" in first
    assert "changed: true" in first
    assert "changed: false" in second
    assert "sequence: 2" in second
    assert first != second


def test_state_diff_detects_added_and_removed_lines():
    browser_observation(3, "https://example.test", "A", "[1] Old\nhello")
    second = browser_observation(3, "https://example.test", "B", "[2] New\nhello")
    assert "state_diff:" in second
    assert "+ [2] New" in second
    assert "- [1] Old" in second


@pytest.mark.asyncio
async def test_browser_state_tool_returns_latest_and_diff():
    observation = browser_observation(4, "https://example.test", "Home", "hello")
    observation_id = next(line.split(": ", 1)[1] for line in observation.splitlines() if line.startswith("observation_id:"))
    latest = await BrowserState().execute(browser_id="4")
    diff = await BrowserState().execute(observation_id=observation_id, mode="diff")
    assert "BROWSER_STATE" in latest.message
    assert "BROWSER_STATE_DIFF" in diff.message
    assert observation_id in diff.message


@pytest.mark.asyncio
async def test_browser_artifact_targeted_query():
    ref = put_artifact("Title\nCreate post\nNotifications\nSearch")
    result = await BrowserArtifact().execute(ref=ref, query="post")
    assert result.message == "Create post"


@pytest.mark.asyncio
async def test_browser_artifact_unknown_ref_is_safe():
    result = await BrowserArtifact().execute(ref="browser://missing")
    assert "unknown or expired" in result.message
