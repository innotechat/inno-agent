from plugins._context_governor.helpers.budget import ContextBudgetConfig, ContextBudgetGovernor


def test_approximate_tokens_is_deterministic():
    governor = ContextBudgetGovernor()
    assert governor.approximate_tokens("1234") == 1
    assert governor.approximate_tokens("12345678") == 2


def test_observation_budget_truncates_predictably():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_observation_tokens=10, max_turn_tokens=100))
    result = governor.govern("x" * 100)
    assert "context budget: truncated" in result
    assert governor.approximate_tokens(result) <= 13


def test_turn_budget_stops_later_observations():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_observation_tokens=10, max_turn_tokens=10))
    first = governor.govern("a" * 40, key="first")
    second = governor.govern("b" * 40, key="second")
    assert first
    assert second == ""


def test_duplicate_observation_is_suppressed():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_turn_tokens=100))
    first = governor.govern("same observation", key="browser-1")
    second = governor.govern("same observation", key="browser-1")
    assert first
    assert second == ""
    assert governor.metrics.duplicates_suppressed == 1


def test_duplicate_observation_still_counts_raw_context():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_turn_tokens=100))
    text = "same observation"
    governor.govern(text, key="browser-1")
    raw_after_first = governor.metrics.raw_tokens
    governor.govern(text, key="browser-1")
    assert governor.metrics.observations == 2
    assert governor.metrics.raw_tokens == raw_after_first * 2
    assert governor.metrics.governed_tokens == raw_after_first
    assert governor.metrics.reduction_percent > 0


def test_actionable_priority_gets_larger_budget():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_observation_tokens=5, max_tool_result_tokens=12, max_turn_tokens=30))
    normal = governor.govern("x" * 40, priority="normal", key="normal")
    actionable = governor.govern("y" * 40, priority="actionable", key="actionable")
    assert governor.approximate_tokens(actionable) > governor.approximate_tokens(normal)


def test_metrics_report_reduction():
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_observation_tokens=5, max_turn_tokens=20))
    governor.govern("x" * 100, key="a")
    assert governor.metrics.raw_tokens > governor.metrics.governed_tokens
    assert governor.metrics.reduction_percent > 0
