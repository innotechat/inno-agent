# Context Governor

## Purpose

Keep browser automation context small by separating **observation** from **full-page artifacts**. The agent receives compact state metadata by default and explicitly retrieves only the content it needs.

## Current implementation

- deterministic bounded browser observations
- browser result history interception
- compact browser system-prompt state
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

Use `browser_artifact` only when the compact observation is insufficient. This prevents repeated page bodies from accumulating in LLM context.

## Safety boundaries

- State and artifact stores are process-local and bounded.
- References expire and unknown/expired references return a safe error.
- Browser close invalidates the corresponding latest state and observation.
- `close_all` clears all browser state.
- Full content is never automatically injected into the browser system prompt.
- Screenshots remain metadata/path references rather than binary prompt payloads.
- This layer does not publish, send, delete, purchase, or otherwise perform high-impact social actions; action safety belongs to the next phase.

## Design rule

**Observe small. Store large. Retrieve on demand. Measure everything.**
