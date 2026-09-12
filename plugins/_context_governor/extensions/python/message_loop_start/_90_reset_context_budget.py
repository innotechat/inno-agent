from __future__ import annotations

from typing import Any

from helpers.extension import Extension
from plugins._context_governor.helpers.budget import get_agent_governor


class ResetContextBudget(Extension):
    """Reset the per-turn budget at the start of each agent message-loop iteration."""

    def execute(self, data: dict[str, Any] | None = None, **kwargs: Any):
        if self.agent is not None:
            get_agent_governor(self.agent).reset_turn()
