from __future__ import annotations

from typing import Any

from plugins._context_governor.helpers.governor import govern_tool_result


def govern_browser_tool_result(data: dict[str, Any]) -> None:
    """Mutate a hist_add_tool_result payload in place when it is browser output."""
    tool_name = str(data.get("tool_name") or "")
    if tool_name.lower() in {"browser", "web_browser"} and "tool_result" in data:
        data["tool_result"] = govern_tool_result(tool_name, data["tool_result"])
