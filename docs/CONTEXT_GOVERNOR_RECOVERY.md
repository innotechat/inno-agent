# Context Governor Recovery

If work is interrupted, resume from the current `feat/context-governor-v6` GitHub state rather than assuming the local checkout is current.

## Safe checkpoint
- Baseline: `inno-baseline-0-v2.11`
- Base branch: `main`
- Feature branch: `feat/context-governor-v6`
- Current verified HEAD: `d06a93cc2e32717a5879fc0ec78efa6263cfda9b`
- PR: #1 (Draft, open)

## Phase 2 verification
- Browser lifecycle integration tests: passed in CI.
- Context Governor unit tests: passed in CI.
- Synthetic browser benchmark: passed in CI.
- Realistic offline browser-observation benchmark: passed in CI.
- The realistic benchmark uses representative offline fixtures; it is not a live-site or provider billing measurement.
- Browser full-document artifacts remain recoverable through explicit references.

## Important Safety Boundaries
- Do not merge PR #1 yet.
- Do not change global `ctx_length`.
- Do not rewrite history compression.
- Do not change vision/screenshot architecture.
- Do not change Responses API state handling in this phase.
- Do not silently treat offline benchmark numbers as production token savings.

## Phase 3 boundary
Phase 2 is complete only after the verified CI state above remains green. Phase 3 must not start automatically; obtain explicit approval first.
