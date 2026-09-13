from __future__ import annotations

from typing import Any

from helpers.extension import Extension
from plugins._context_governor.helpers.budget import get_agent_governor


class BudgetObservation(Extension):
    """Apply the per-agent context budget after browser compaction."""

    def execute(self, data: dict[str, Any] | None = None, **kwargs: Any):
        if not isinstance(data, dict) or self.agent is None:
            return
        tool_name = str(data.get("tool_name") or "").lower()
        if tool_name not in {"browser", "web_browser"} or "tool_result" not in data:
            return
        result = str(data["tool_result"] or "")
        if not result:
            return
        governor = get_agent_governor(self.agent)
        priority = "actionable" if result.startswith("BROWSER_OBSERVATION") else "normal"
        key = f"{tool_name}:{getattr(self.agent, 'number', 0)}"
        budgeted = governor.govern(result, priority=priority, key=key)
        if budgeted:
            data["tool_result"] = budgeted
        else:
            data["tool_result"] = "BROWSER_OBSERVATION\ncontext_budget: turn budget exhausted; full artifact remains recoverable"
