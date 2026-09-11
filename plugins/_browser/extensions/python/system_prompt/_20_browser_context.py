from __future__ import annotations

from typing import Any

from agent import LoopData
from helpers.extension import Extension
from plugins._browser.helpers.runtime import get_runtime
from plugins._context_governor.helpers.governor import browser_observation


class BrowserContextPrompt(Extension):
    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ):
        if not self.agent:
            return

        runtime = await get_runtime(self.agent.context.id, create=False)
        if not runtime:
            return

        try:
            listing = await runtime.call("list")
        except Exception:
            return

        browsers = listing.get("browsers") or []
        if not browsers:
            return

        rows = ["browser id|url|title"]
        for browser in browsers:
            rows.append(
                f"{browser.get('id')}|{browser.get('currentUrl', '')}|{browser.get('title', '')}"
            )

        section = ["currently open web browsers", "\n".join(rows)]
        last_id = listing.get("last_interacted_browser_id")
        if last_id:
            try:
                state = await runtime.call("state", last_id)
                # Do not inject the full DOM/document into every system prompt.
                # The browser tool remains the explicit retrieval path.
                section.extend(
                    [
                        "",
                        "last interacted web browser",
                        browser_observation(
                            state.get("id"),
                            state.get("currentUrl", ""),
                            state.get("title", ""),
                        ),
                        "full page content is available through the browser content/detail actions when explicitly requested",
                    ]
                )
            except Exception:
                pass

        system_prompt.append("\n".join(section))
