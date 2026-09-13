from __future__ import annotations

import pytest

from helpers.tool import Response, Tool
from plugins._context_governor.helpers.action_safety import (
    ACTION_AUDIT_LOG,
    ACTION_IDEMPOTENCY_STORE,
    browser_action_fingerprint,
    decide_browser_action,
)
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


class _FakeLog:
    id = "safety-test-log"

    def update(self, **kwargs):
        self.updated = kwargs


class _FakeContext:
    id = "ctx-safety"
    type = None

    def get_data(self, key):
        return None


class _FakeAgent:
    agent_name = "safety-test-agent"
    context = _FakeContext()

    def hist_add_tool_result(self, *args, **kwargs):
        pass


class _FakeBrowserTool(Tool):
    async def execute(self, **kwargs):
        return Response(message="success: true", break_loop=False)

    def get_log_object(self):
        return _FakeLog()


@pytest.fixture(autouse=True)
def clean_safety_state():
    ACTION_IDEMPOTENCY_STORE.clear()
    ACTION_AUDIT_LOG.clear()
    BROWSER_STATE_STORE.clear()
    yield
    ACTION_IDEMPOTENCY_STORE.clear()
    ACTION_AUDIT_LOG.clear()
    BROWSER_STATE_STORE.clear()


def test_high_impact_requires_confirmation():
    decision = decide_browser_action({"action": "publish"})
    assert decision.allowed is False
    assert decision.risk == "high"


def test_confirmation_is_bound_to_observation_and_action_fingerprint():
    args = {
        "action": "publish",
        "browser_id": 7,
        "observation_id": "obs-1",
        "ref": 12,
        "text": "approved post",
        "confirm": True,
    }
    first = browser_action_fingerprint(args)
    changed = browser_action_fingerprint({**args, "ref": 13})
    assert first != changed
    assert decide_browser_action(args).allowed is True


@pytest.mark.asyncio
async def test_completed_high_impact_action_is_not_repeated():
    tool = _FakeBrowserTool(_FakeAgent(), "browser", None, {}, "", None)
    args = {
        "action": "publish",
        "browser_id": 7,
        "observation_id": "obs-1",
        "ref": 12,
        "text": "approved post",
        "confirm": True,
    }
    await tool.before_execution(**args)
    fingerprint = browser_action_fingerprint({**args, "context_id": "ctx-safety"})
    ACTION_IDEMPOTENCY_STORE.mark_completed(fingerprint)
    with pytest.raises(ValueError, match="duplicate high-impact"):
        await tool.before_execution(**args)


@pytest.mark.asyncio
async def test_stale_observation_is_blocked():
    BROWSER_STATE_STORE.snapshot(
        browser_id=7,
        url="https://example.test/current",
        title="Current",
        content="Current page",
    )
    latest = BROWSER_STATE_STORE.latest(7)
    assert latest is not None

    tool = _FakeBrowserTool(_FakeAgent(), "browser", None, {}, "", None)
    with pytest.raises(ValueError, match="stale"):
        await tool.before_execution(
            action="click",
            browser_id=7,
            observation_id="old-observation",
            ref=12,
        )


def test_audit_log_does_not_store_secret_values():
    decision = decide_browser_action({"action": "publish", "confirm": True})
    ACTION_AUDIT_LOG.record(
        decision=decision,
        fingerprint="abc123",
        status="completed",
        args={"action": "publish", "access_token": "SECRET", "text": "hello"},
    )
    entry = ACTION_AUDIT_LOG.entries()[-1]
    assert "SECRET" not in str(entry)
    assert entry["args"]["access_token"] == "[REDACTED]"
