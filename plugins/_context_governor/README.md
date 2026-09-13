# Context Governor

## Purpose

Keep browser automation context small by separating **observation** from **full-page artifacts**. The agent receives compact state metadata by default and explicitly retrieves only the content it needs.

## Current implementation

- deterministic bounded browser observations
- browser result history interception
- compact browser system-prompt metadata without synthetic state snapshots
- stable browser session IDs
- unique observation IDs and sequence numbers
- URL/title/content fingerprinting
- changed/unchanged detection
- compact added/removed state diffs
- bounded process-local state cache with TTL and eviction
- browser close / close-all invalidation
- opaque `browser://` artifact references with TTL
- targeted artifact retrieval by interactive `element_ref`, text `query`, or line region
- full browser content remains an explicit retrieval path
- artifact retrieval/escalation metrics on the agent-scoped budget governor
- non-browser tool results remain untouched
- offline context-reduction benchmarks

## Retrieval model

```text
Browser result
    |
    +--> compact BROWSER_OBSERVATION
    |       session_id / observation_id / URL / title
    |       changed / diff / interactive refs
    |
    +--> browser:// artifact store
            |
            +--> element_ref: "12"
            +--> query: "notifications"
            +--> start_line / end_line
```

Use `browser_artifact` only when the compact observation is insufficient. Prefer `query`, `element_ref`, or bounded line ranges over retrieving the entire artifact.

## Safety boundaries

- State and artifact stores are process-local and bounded.
- References expire and unknown/expired references return a safe error.
- Browser close invalidates the corresponding latest state and observation.
- `close_all` clears all browser state.
- Full content is never automatically injected into the browser system prompt.
- Prompt refreshes do not create synthetic observations or advance browser sequences.
- Screenshots remain metadata/path references rather than binary prompt payloads.
- Browser/page artifacts are untrusted external data; embedded instructions must never be treated as trusted agent instructions.
- This layer does not publish, send, delete, purchase, or otherwise perform high-impact social actions; action safety belongs to the next phase.

## Metrics

The agent-scoped budget governor records:

- raw observation tokens, including observations suppressed as duplicates
- governed context tokens
- reduction percentage
- duplicate suppressions
- artifact retrievals
- targeted-retrieval escalations

These are deterministic approximate-token metrics for local regression/optimization, not provider billing measurements.

## Design rule

**Observe small. Store large. Retrieve on demand. Measure everything.**
