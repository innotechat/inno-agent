from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContextBudgetConfig:
    """Deterministic context budgets. Token estimates are intentionally conservative."""

    max_observation_tokens: int = 2500
    max_tool_result_tokens: int = 3000
    max_turn_tokens: int = 10000
    chars_per_token: float = 4.0


@dataclass
class BudgetMetrics:
    raw_tokens: int = 0
    governed_tokens: int = 0
    observations: int = 0
    escalations: int = 0
    artifact_retrievals: int = 0
    duplicates_suppressed: int = 0

    @property
    def reduction_percent(self) -> float:
        if self.raw_tokens <= 0:
            return 0.0
        return round((1 - self.governed_tokens / self.raw_tokens) * 100, 2)


@dataclass
class ContextBudgetGovernor:
    """Stateful per-turn budget governor; full artifacts stay outside this context."""

    config: ContextBudgetConfig = field(default_factory=ContextBudgetConfig)
    metrics: BudgetMetrics = field(default_factory=BudgetMetrics)
    _turn_tokens: int = 0
    _seen: set[str] = field(default_factory=set)

    def reset_turn(self) -> None:
        self._turn_tokens = 0
        self._seen.clear()

    def approximate_tokens(self, text: Any) -> int:
        value = str(text or "")
        if not value:
            return 0
        return max(1, int((len(value) + self.config.chars_per_token - 1) / self.config.chars_per_token))

    def _truncate_tokens(self, text: str, token_budget: int) -> str:
        limit = max(int(token_budget), 1)
        if self.approximate_tokens(text) <= limit:
            return text

        max_chars = max(int(limit * self.config.chars_per_token), 1)
        # Keep the marker deliberately compact so even small budgets retain an
        # explicit truncation signal without exceeding the requested budget.
        marker = "context budget: truncated"
        marker_chars = len(marker)
        if max_chars <= marker_chars:
            return marker[:max_chars]

        payload_chars = max_chars - marker_chars
        head = max(payload_chars * 2 // 3, 0)
        tail = max(payload_chars - head, 0)
        if head and tail:
            result = text[:head] + marker + text[-tail:]
        elif head:
            result = text[:head] + marker
        else:
            result = marker

        # Keep the final estimate strictly within the requested budget.
        while self.approximate_tokens(result) > limit and result:
            result = result[:-1]
        return result

    def govern(self, text: Any, *, priority: str = "normal", key: str = "") -> str:
        """Apply observation, tool-result, and remaining per-turn budgets deterministically."""
        raw = str(text or "")
        if not raw.strip():
            return ""

        # Preserve structured observation line boundaries while removing noisy spacing.
        value = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()).strip()
        if not value:
            return ""

        fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()
        seen_key = f"{key}\0{fingerprint}" if key else fingerprint
        if key and seen_key in self._seen:
            self.metrics.duplicates_suppressed += 1
            return ""
        if key:
            self._seen.add(seen_key)

        self.metrics.raw_tokens += self.approximate_tokens(value)
        self.metrics.observations += 1

        per_item = self.config.max_observation_tokens
        if priority in {"critical", "actionable"}:
            per_item = min(self.config.max_tool_result_tokens, max(per_item, self.config.max_tool_result_tokens))
        remaining = max(self.config.max_turn_tokens - self._turn_tokens, 0)
        budget = min(per_item, remaining)
        if budget <= 0:
            return ""

        governed = self._truncate_tokens(value, budget)
        used = self.approximate_tokens(governed)
        self._turn_tokens += used
        self.metrics.governed_tokens += used
        return governed

    def note_escalation(self) -> None:
        self.metrics.escalations += 1

    def note_artifact_retrieval(self) -> None:
        self.metrics.artifact_retrievals += 1


def get_agent_governor(agent: Any) -> ContextBudgetGovernor:
    """Return an agent-scoped governor without changing the core agent model."""
    governor = getattr(agent, "_context_budget_governor", None)
    if not isinstance(governor, ContextBudgetGovernor):
        governor = ContextBudgetGovernor()
        setattr(agent, "_context_budget_governor", governor)
    return governor


def budget_observation(text: Any, budget: int = 2500) -> str:
    """Stateless helper for callers that only need a deterministic item budget."""
    governor = ContextBudgetGovernor(ContextBudgetConfig(max_observation_tokens=budget, max_turn_tokens=budget))
    return governor.govern(text)
