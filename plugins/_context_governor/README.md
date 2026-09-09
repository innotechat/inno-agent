# Context Governor v1

## Purpose

Prevent oversized browser observations from becoming unbounded LLM context.

## Current status

Phase A is intentionally isolated and safe:

- deterministic bounded document compaction
- browser observation formatter
- non-browser results remain untouched
- unit tests included

## Next patch

Wire the Governor into the browser system-prompt extension and browser tool-result lifecycle. Preserve full artifacts for on-demand retrieval. Do not change global context limits or history compression yet.

## Design rule

**Observe small. Store large. Retrieve on demand. Measure everything.**
