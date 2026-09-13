from __future__ import annotations

from plugins._context_governor.helpers.budget import get_agent_governor
from plugins._context_governor.extensions.python.message_loop_start._90_reset_context_budget import ResetContextBudget
from plugins._context_governor.extensions.python.hist_add_tool_result._91_budget_observation import BudgetObservation


class FakeAgent:
    number = 0


def test_budget_extension_uses_agent_scoped_governor():
    agent = FakeAgent()
    reset = ResetContextBudget(agent=agent)
    reset.execute()
    governor = get_agent_governor(agent)
    payload = {"tool_name": "browser", "tool_result": "BROWSER_OBSERVATION\n" + "x" * 16000}
    BudgetObservation(agent=agent).execute(payload)
    assert governor.metrics.raw_tokens > 0
    assert governor.metrics.governed_tokens > 0
    assert governor.metrics.governed_tokens <= governor.config.max_tool_result_tokens
    assert "BROWSER_OBSERVATION" in payload["tool_result"]


def test_turn_reset_allows_new_budget_after_previous_turn():
    agent = FakeAgent()
    governor = get_agent_governor(agent)
    BudgetObservation(agent=agent).execute({"tool_name": "browser", "tool_result": "BROWSER_OBSERVATION\n" + "a" * 16000})
    first_turn_used = governor._turn_tokens
    assert first_turn_used > 0
    ResetContextBudget(agent=agent).execute()
    assert governor._turn_tokens == 0
    assert governor._seen == set()
