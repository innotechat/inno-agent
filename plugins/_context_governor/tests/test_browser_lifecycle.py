from __future__ import annotations

import pytest

from helpers import extension, plugins
from helpers.tool import Response
from plugins._browser.extensions.python.system_prompt._20_browser_context import BrowserContextPrompt
from plugins._browser.tools.browser import Browser
from plugins._context_governor.helpers.artifacts import ArtifactStore
from plugins._context_governor.helpers.governor import format_browser_result, govern_tool_result
from plugins._context_governor.tools.browser_artifact import BrowserArtifact


class _FakeLog:
    def __init__(self):
        self.updated = None

    def update(self, content: str):
        self.updated = content


class _FakeAgent:
    def __init__(self):
        self.agent_name = "test-agent"
        self.captured = None
        self.context = type("Context", (), {"id": "test-context"})()

    def hist_add_tool_result(self, tool_name: str, tool_result: str, **kwargs):
        data = {"tool_name": tool_name, "tool_result": tool_result, **kwargs}
        # Exercise the same extension hook used by Agent.hist_add_tool_result().
        extension.call_extensions_sync("hist_add_tool_result", agent=None, data=data)
        self.captured = data


@pytest.mark.asyncio
async def test_browser_tool_result_flows_through_real_tool_lifecycle():
    agent = _FakeAgent()
    browser = Browser(agent, "browser", None, {}, "", None)
    browser.log = _FakeLog()

    raw_document = "Dashboard\n[12] Create post\n[17] Search\n" + ("visible content " * 2000)
    formatted = browser._format_result(
        "click",
        {
            "browser_id": 2,
            "currentUrl": "https://example.test/dashboard",
            "title": "Dashboard",
            "success": True,
            "document": raw_document,
        },
    )

    await browser.after_execution(Response(message=formatted, break_loop=False))

    assert agent.captured is not None
    assert agent.captured["tool_name"] == "browser"
    history_result = agent.captured["tool_result"]
    assert history_result == formatted
    assert history_result.startswith("BROWSER_OBSERVATION\n")
    assert "artifact_ref: browser://" in history_result
    assert "[12] Create post" in history_result
    assert "[17] Search" in history_result
    assert len(history_result) < len(raw_document)
    assert browser.log.updated == history_result


@pytest.mark.asyncio
async def test_browser_artifact_tool_retrieves_full_document():
    from plugins._context_governor.helpers.artifacts import put_artifact

    value = "FULL BROWSER DOCUMENT " * 100
    ref = put_artifact(value)
    tool = BrowserArtifact(_FakeAgent(), "browser_artifact", None, {}, "", None)
    response = await tool.execute(ref=ref)
    assert response.message == value
    assert response.break_loop is False


@pytest.mark.asyncio
async def test_browser_artifact_tool_rejects_invalid_reference():
    tool = BrowserArtifact(_FakeAgent(), "browser_artifact", None, {}, "", None)
    response = await tool.execute(ref="browser://invalid")
    assert "unknown or expired" in response.message
    assert response.break_loop is False


def test_context_governor_plugin_is_discoverable_as_tool():
    tool_paths = plugins.get_enabled_plugin_paths(None, "tools")
    assert any(path.replace("\\", "/").endswith("_context_governor/tools") for path in tool_paths)


def test_hist_add_tool_result_extension_is_registered():
    classes = extension._get_extension_classes("hist_add_tool_result", agent=None)
    names = {cls.__name__ for cls in classes}
    assert "GovernObservation" in names


@pytest.mark.asyncio
async def test_browser_context_prompt_never_fetches_full_content(monkeypatch):
    calls: list[tuple[str, object]] = []

    class _Runtime:
        async def call(self, action, *args):
            calls.append((action, args))
            if action == "list":
                return {
                    "browsers": [
                        {"id": 2, "currentUrl": "https://example.test", "title": "Dashboard"}
                    ],
                    "last_interacted_browser_id": 2,
                }
            if action == "state":
                return {"id": 2, "currentUrl": "https://example.test", "title": "Dashboard"}
            raise AssertionError(f"unexpected runtime action: {action}")

    async def fake_get_runtime(*args, **kwargs):
        return _Runtime()

    module = __import__(
        "plugins._browser.extensions.python.system_prompt._20_browser_context",
        fromlist=["get_runtime"],
    )
    monkeypatch.setattr(module, "get_runtime", fake_get_runtime)

    extension_instance = BrowserContextPrompt(_FakeAgent())
    prompt: list[str] = []
    await extension_instance.execute(system_prompt=prompt)

    assert prompt
    assert "BROWSER_OBSERVATION" in prompt[0]
    assert [action for action, _ in calls] == ["list", "state"]
    assert "full page content" in prompt[0]


def test_governance_is_idempotent_after_browser_formatting():
    formatted = format_browser_result(
        "click",
        {
            "browser_id": 2,
            "url": "https://example.test",
            "title": "Dashboard",
            "document": "Dashboard\n[12] Create post\nRecent activity",
        },
    )
    assert govern_tool_result("browser", formatted) == formatted


def test_screenshot_metadata_is_preserved_without_binary_in_context():
    result = format_browser_result(
        "screenshot",
        {
            "path": "/tmp/browser-shot.png",
            "browser_id": 2,
            "url": "https://example.test",
            "title": "Dashboard",
            "screenshot": "/tmp/browser-shot.png",
            "success": True,
        },
    )
    assert "/tmp/browser-shot.png" in result
    assert "success" in result
    assert "BROWSER_OBSERVATION" not in result


def test_expired_artifact_is_rejected():
    store = ArtifactStore(ttl_seconds=1)
    now = 100.0
    import plugins._context_governor.helpers.artifacts as artifacts_module

    original = artifacts_module.time.monotonic
    artifacts_module.time.monotonic = lambda: now
    try:
        ref = store.put("document")
        artifacts_module.time.monotonic = lambda: now + 2
        with pytest.raises(KeyError, match="unknown or expired"):
            store.get(ref)
    finally:
        artifacts_module.time.monotonic = original
