from __future__ import annotations

from typing import Any

from helpers.extension import Extension
from plugins._context_governor.helpers.governor import govern_tool_result


class GovernObservation(Extension):
    """Bound browser results before they become persistent history."""

    def execute(self, data: dict[str, Any] | None = None, **kwargs: Any):
        if not isinstance(data, dict):
            return
        tool_name = str(data.get("tool_name") or "").lower()
        if tool_name not in {"browser", "web_browser"}:
            return
        if "tool_result" in data:
            data["tool_result"] = govern_tool_result(tool_name, data["tool_result"])
