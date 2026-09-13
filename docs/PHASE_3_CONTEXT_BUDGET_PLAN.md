# Phase 3 — Context Budget Governor

## Goal

Add a second token-efficiency layer above the validated Context Governor. The layer must reduce redundant LLM context without reducing reasoning or vision quality and without changing global model context limits.

## Safe implementation sequence

1. **Budget core** — deterministic token estimation, per-observation budget, per-tool-result budget, and per-turn budget.
2. **Priority retention** — preserve critical/actionable state before normal text.
3. **Deduplication** — suppress unchanged repeated observations within a turn using stable fingerprints.
4. **Integration** — connect budgets to browser/history lifecycle with explicit turn boundaries.
5. **Targeted escalation** — prefer metadata/interactive/detail levels; retrieve full artifacts only when explicitly needed.
6. **Observability** — expose raw tokens, governed tokens, reduction %, observations, suppressions, escalations, and artifact retrievals.
7. **Regression validation** — unit, browser lifecycle, benchmark, build/type checks, and safety review.

## Initial budgets

```yaml
context_budget:
  max_observation_tokens: 2500
  max_tool_result_tokens: 3000
  max_turn_tokens: 10000
  full_content_default: false
```

These are starting defaults, not provider billing measurements. They must be tuned from repository benchmarks.

## Information priority

1. Critical errors and action preconditions
2. Actionable interactive elements
3. Current URL/title/page state
4. User-requested visible information
5. Relevant visible text
6. Redundant/stale context

## Safety boundaries

- Never discard an action target or precondition silently.
- Full browser artifacts remain recoverable outside prompt context.
- Never modify global context limits.
- Never downgrade the model or vision path.
- Never log credentials, cookies, access tokens, or raw secrets.
- Do not automatically publish, send, delete, purchase, or perform other irreversible social actions.
- Keep provider-specific tokenization isolated behind adapters.

## Exit criteria

Phase 3 is complete only when the integrated implementation has deterministic budgets, measurable reduction, preserved action-relevant information, passing tests/benchmarks/CI, and a documented security review.

Phase 4 must not start automatically after this phase.
