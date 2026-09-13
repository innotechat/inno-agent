# Phase 4 — Browser State / Retrieval

## Goal

Make browser automation state-aware so the agent reasons from compact state snapshots and retrieves only what is needed.

## Implemented

- [x] Stable browser session IDs
- [x] Observation IDs and sequence numbers
- [x] URL/title/content fingerprinting
- [x] Changed/unchanged detection
- [x] Compact state diffs
- [x] Artifact references and bounded artifact store
- [x] Targeted retrieval by element ref
- [x] Targeted retrieval by text query
- [x] Targeted retrieval by line region
- [x] TTL expiry
- [x] Snapshot eviction
- [x] Browser close invalidation
- [x] Close-all invalidation
- [x] Compact unchanged observations
- [x] Browser lifecycle integration
- [x] Offline repeated-state benchmark
- [x] Tests for stale references and isolation

## Verification

The strongest available repository verification is GitHub Actions. The current PR contains a dedicated workflow that runs the Phase 1–4 test suites and all three offline benchmarks.

Local execution is not currently available from this environment because direct GitHub network access from the execution container is unavailable. Targeted logic has been independently exercised for state lifecycle, stale observation invalidation, artifact-reference preservation, element retrieval, and hard retrieval limits.

## Acceptance

Phase 4 is ready for completion only when the current branch CI is green. Do not merge or start Phase 5 based solely on local/static verification.
