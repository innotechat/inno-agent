"""Offline benchmark for repeated browser state context reduction.

This measures serialization size only. It is not a provider billing/token report.
"""
from __future__ import annotations

from plugins._context_governor.helpers.artifacts import ARTIFACT_STORE
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE
from plugins._context_governor.helpers.governor import browser_observation


def approx_tokens(text: str) -> int:
    return max(len(text) // 4, 0)


def main() -> None:
    BROWSER_STATE_STORE.clear()
    ARTIFACT_STORE.clear()
    document = "\n".join(
        ["Dashboard", "[12] Create post", "[17] Search", "[23] Notifications"]
        + [f"Recent activity item {i}: representative browser content" for i in range(1, 160)]
    )
    observations = [
        browser_observation(1, "https://example.test/dashboard", "Dashboard", document)
        for _ in range(5)
    ]
    raw_total = len(document) * len(observations)
    governed_total = sum(len(item) for item in observations)
    repeated_savings = 100 * (1 - governed_total / raw_total)
    print({
        "type": "browser_state_repeated_observation",
        "observations": len(observations),
        "raw_chars": raw_total,
        "governed_chars": governed_total,
        "raw_approx_tokens": approx_tokens(document) * len(observations),
        "governed_approx_tokens": sum(approx_tokens(item) for item in observations),
        "repeated_context_reduction_percent": round(repeated_savings, 2),
        "artifact_refs_preserved": sum("artifact_ref: browser://" in item for item in observations),
        "note": "offline synthetic benchmark; not live provider billing measurement",
    })


if __name__ == "__main__":
    main()
