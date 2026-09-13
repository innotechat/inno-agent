# Inno Agent — Context Governor Implementation Plan

**Status:** READY FOR IMPLEMENTATION
**Scope:** Browser + social-platform automation first
**Baseline:** `inno-baseline-0-v2.11` / `6a6cecff`
**Workflow:** AUDIT → MEASURE → DESIGN → PATCH → TEST → BENCHMARK

---

## 1. Executive Decision

Do **not** solve token growth by simply lowering `ctx_length`, disabling vision, or making history compression more aggressive.

The main architectural change should be:

```text
Browser / Social Runtime
        |
        v
Observation Governor
   |              |
   |              +--> Full DOM / screenshot / artifact store
   |                         |
   v                         v
Compact observation      Stable reference
   |
   v
Agent history / prompt
```

The LLM should normally receive a **small, task-relevant observation**, while full browser artifacts remain available on demand.

This is a prevention architecture: unnecessary tokens should not enter the context in the first place.

---

## 2. Audit Findings

The audit output confirms two independent browser-context injection paths.

### P0-A — Browser system prompt injects the full page document

File:

`plugins/_browser/extensions/python/system_prompt/_20_browser_context.py`

Current behavior:

1. Gets the last interacted browser.
2. Calls `runtime.call("state", last_id)`.
3. Calls `runtime.call("content", last_id, None)`.
4. Extracts `content["document"]`.
5. Appends the complete document to the system prompt.

Critical pattern:

```python
content = await runtime.call("content", last_id, None)
document = content.get("document") if isinstance(content, dict) else ""
...
"page content↓",
str(document),
```

Therefore a large DOM/document can be re-injected during every prompt build. This is the first implementation target.

### P0-B — Browser tool content becomes normal history

File:

`plugins/_browser/tools/browser.py`

The `content` action calls the runtime and `_format_result()` returns the document directly when the result contains only `document`:

```python
if action == "content" and isinstance(result, dict):
    if set(result.keys()) == {"document"}:
        return str(result.get("document") or "")
```

Then the common tool lifecycle in `helpers/tool.py` sanitizes the response and calls:

```python
self.agent.hist_add_tool_result(...)
```

`agent.py` then routes tool results through:

```python
extension.call_extensions_sync("hist_add_tool_result", self, data=data)
```

So large browser observations can enter persistent agent history as raw text.

### P1 — Current context-window subsystem measures but does not prevent inflation

`plugins/_context_window/helpers/usage.py` already measures:

- messages
- system tools
- skills
- MCP tools
- system prompt
- extras
- provider input/output usage

This is valuable and should be preserved. It gives us instrumentation for the Governor rather than requiring a new token accounting system.

### P1 — History compression is reactive

`helpers/history.py` compresses once the history exceeds configured limits. It can:

- trim large messages
- summarize topic attention
- merge old topics into bulks
- remove old bulks

This protects the context window, but it happens **after** large observations have already entered the history model.

The new Governor must sit earlier in the pipeline.

### P1 — Responses API state must not be broken

`agent.py` contains incremental Responses API state handling and clears provider response state when history compression occurs. The implementation must preserve this behavior.

Do not rewrite Responses handling during Phase 1.

---

## 3. Existing Configuration Evidence

The audit found:

```text
ctx_length defaults include 128000 / 200000
ctx_history defaults include 0.7
vision may be enabled
max_embeds defaults include 10
```

Relevant files include:

- `plugins/_model_config/helpers/model_config.py`
- `plugins/_model_config/mode_presets_fallback.yaml`
- `helpers/tokens.py`
- `helpers/history.py`

These values are **not** the first thing to change. They are safety limits, not the root fix.

---

## 4. Target Architecture

Create a focused component, preferably:

```text
plugins/_context_governor/
    README.md
    config.py
    helpers/
        governor.py
        observations.py
        artifacts.py
        policy.py
    extensions/python/
        hist_add_tool_result/
            _90_govern_observation.py
        system_prompt/
            _20_browser_context.py  # only if browser-specific interception remains necessary
    tests/
        test_governor.py
        test_browser_observation.py
        test_budget.py
```

The exact extension placement may be adjusted after the first implementation pass. Reuse Agent Zero extension hooks instead of modifying core flow wherever possible.

### Core concepts

#### Observation

A normalized, compact representation of what the agent needs to decide its next action.

Example:

```text
BROWSER_OBSERVATION
browser_id: 2
url: https://example.com/dashboard
title: Dashboard

interactive_elements:
- [12] Create post
- [17] Search
- [23] Notifications

visible_text:
Account dashboard loaded.
3 pending notifications.

artifact:
browser://session/2/dom/456
```

#### Artifact

The full DOM, accessibility tree, screenshot, or other large payload stored outside the normal prompt/history representation.

#### Reference

A short stable identifier allowing a later tool call to retrieve the artifact if required.

---

## 5. Governor Policy

Implement policy in this order:

### Level 0 — Metadata only

Always safe to include:

- browser id
- URL
- title
- current page/route
- action status
- success/error state

### Level 1 — Compact visible/interactive observation

Include only information useful for the next action:

- interactive controls
- relevant labels
- visible text around the active task
- selected/focused element
- relevant forms
- small status messages

### Level 2 — Targeted detail

Retrieve a specific selector, element, section, or bounded DOM fragment only when needed.

### Level 3 — Full artifact

Full DOM/document/screenshot is an explicit escalation path, not the default prompt payload.

---

## 6. Budget Rules

Initial conservative defaults for Phase 1 should be configurable, not hard-coded throughout the code.

Suggested starting policy:

```yaml
context_governor:
  enabled: true
  browser:
    max_observation_tokens: 2500
    max_visible_text_tokens: 1200
    max_interactive_elements: 80
    max_dom_fragment_tokens: 3000
    full_content_default: false
  history:
    max_tool_result_tokens: 3000
  artifacts:
    enabled: true
    retain_full_document: true
```

These are **starting values for benchmarking**, not final performance claims. Tune them from measured workloads.

Hard safety principle:

> If a payload exceeds its budget, compact it or store it as an artifact. Never silently push an unbounded payload into normal history.

---

## 7. Browser System-Prompt Change

Current behavior injects the complete last-browser document.

Replace the default behavior with a compact observation.

Target behavior:

```text
currently open web browsers
browser id|url|title
2|https://...|Dashboard

last interacted web browser
browser id|url|title
2|https://...|Dashboard

browser observation↓
interactive_elements:
- [12] Create post
- [17] Search
...
visible_text:
...
artifact: browser://...
```

Do **not** call full `content()` merely to construct the system prompt unless a policy explicitly requires it.

If the browser runtime currently has no compact observation API, implement a bounded extractor in the Governor/browser helper rather than passing the full document through unchanged.

---

## 8. Tool-Result Interception

Use the existing extension hook:

```python
hist_add_tool_result
```

The Governor should inspect tool results before they become persistent history.

Pseudo-flow:

```python
raw_result
   |
   +-- small --> keep as-is
   |
   +-- browser/social observation --> compact + artifact reference
   |
   +-- huge generic result --> bounded summary + artifact/reference
   |
   +-- error/auth/security result --> preserve required details
```

Do not globally summarize every tool response. Generic tool behavior can be semantic and must not be damaged by an over-broad truncation policy.

---

## 9. Browser/Social Platform Strategy

The system is being optimized primarily for automation, especially browser and social platforms.

Therefore observations should prioritize:

1. current URL/page
2. authenticated/session state indicator without exposing secrets
3. actionable controls
4. forms and required fields
5. confirmation/status messages
6. visible task-relevant content
7. stable element references
8. artifact references

Never place:

- cookies
- access tokens
- passwords
- raw authorization headers
- private credentials

into an LLM observation unless a separately designed secure mechanism explicitly requires it.

For social platforms, the Governor should also preserve anti-automation safety signals such as:

- rate-limit responses
- CAPTCHA/challenge state
- login expiry
- account restriction warnings
- failed submission status

These should not be hidden by aggressive compaction.

---

## 10. Retrieval / Escalation Design

The compact observation must not make the browser blind.

Add explicit retrieval capability, for example:

```text
browser_detail(selector)
browser_content(selector)
browser_artifact(reference)
```

Reuse existing browser actions where possible. Do not create duplicate APIs if `detail`, `content`, `evaluate`, or existing runtime operations can safely support the same behavior.

Ideal agent behavior:

```text
Observe compactly
      ↓
Decide
      ↓
Need more detail?
  /          \
 no           yes
 |             |
act       targeted retrieval
```

---

## 11. Observability Requirements

Extend the existing context-window usage data rather than creating a parallel incompatible metric system.

Recommended additional fields:

```text
raw_observation_tokens
compacted_observation_tokens
artifact_tokens_saved
observation_count
full_retrieval_count
full_retrieval_tokens
compaction_count
compaction_reason
```

At minimum, every governed observation should make it possible to answer:

- how large was the raw payload?
- how large was the LLM-visible payload?
- was it compacted?
- where was the full payload stored?
- did the agent later retrieve it?

This is essential for proving that token savings did not come at the cost of task failure.

---

## 12. Implementation Phases

### Phase 0 — Freeze and measurement

Already established baseline:

```text
HEAD = 6a6cecff
v2.11
inno-baseline-0-v2.11
working tree clean
```

Do not modify production behavior before recording baseline measurements.

### Phase 1 — Browser observation Governor

Implement:

- config
- artifact storage/reference abstraction
- browser observation normalization
- tool-result interception
- system-prompt compact observation
- tests

No history algorithm rewrite.

### Phase 2 — Targeted retrieval

Add bounded retrieval/escalation and verify that difficult pages remain automatable.

### Phase 3 — Social automation adapters

Build platform-specific observation policies on top of the generic Governor rather than duplicating the entire browser system.

### Phase 4 — Generic large-tool protection

Only after browser benchmarks succeed, consider bounded handling for other oversized tool/MCP outputs.

### Phase 5 — History optimization

Use measured data to decide whether `helpers/history.py` needs tuning. Prefer configuration/extension changes over invasive core rewrites.

---

## 13. Test Plan

Every phase must pass the existing suite plus Governor tests.

### Unit tests

Test:

- small payload remains unchanged
- large browser document becomes compact observation
- artifact reference is generated
- full document is retrievable
- selector detail is bounded
- empty/invalid browser result is safe
- tool errors preserve useful diagnostic information
- sensitive fields are never emitted
- configurable budgets are respected

### Regression tests

Verify:

- normal browser navigation
- click
- type
- submit
- scroll
- screenshot
- multiple browser sessions
- browser close/close_all
- parallel tools
- MCP responses
- Responses API incremental state
- history compression

### Automation tests

Create realistic scenarios:

1. Login → dashboard → create action
2. Search → result selection → detail page
3. Social compose → preview → submit
4. Infinite/large page
5. Page with large scripts/DOM noise
6. Authentication expiry
7. CAPTCHA/rate-limit page

---

## 14. Benchmark Plan

Run the same scenarios before and after the Governor.

Record:

```text
scenario
turns
raw_browser_tokens
prompt_tokens
provider_input_tokens
cached_input_tokens
output_tokens
full_retrieval_count
context_compression_count
latency
success/failure
```

Primary KPI:

```text
LLM-visible browser tokens / raw browser observation tokens
```

Secondary KPIs:

- task success rate
- provider input tokens
- latency
- number of escalation calls
- context compression frequency
- error rate

The optimization is successful only if token usage falls **without materially reducing automation reliability**.

---

## 15. Acceptance Criteria

Phase 1 is accepted only when all are true:

- Full browser document is no longer automatically injected into every system prompt.
- Large browser tool results are not stored raw in normal history by default.
- Full artifacts remain retrievable.
- Browser tasks continue to work.
- Existing tests remain green.
- New Governor tests are green.
- Context-window metrics show raw vs governed size.
- No credential/secret leakage is introduced.
- Responses API state behavior remains intact.
- Baseline comparison demonstrates measurable reduction in LLM-visible browser context.

Do not set an arbitrary percentage target before the benchmark. Measure first, then establish a project KPI from real workloads.

---

## 16. Files To Inspect/Modify

### First implementation pass

```text
plugins/_browser/extensions/python/system_prompt/_20_browser_context.py
plugins/_browser/tools/browser.py
plugins/_browser/helpers/runtime.py
helpers/tool.py
agent.py
plugins/_context_window/helpers/usage.py
```

### Reuse, do not rewrite initially

```text
helpers/history.py
helpers/tokens.py
helpers/llm_result.py
```

### New component

```text
plugins/_context_governor/
```

---

## 17. Commands for Implementation

Start every implementation session with:

```bash
cd ~/projects/inno-agent

git status --short --branch
git log -1 --oneline
git tag --points-at HEAD
```

Create a feature branch:

```bash
git switch -c feat/context-governor
```

Before changes, run targeted tests if available:

```bash
pytest -q plugins/_context_window/tests
pytest -q plugins/_browser/tests
```

Then run the complete test suite used by the repository.

After each logical patch:

```bash
git diff --check
pytest -q
```

Never overwrite the baseline tag.

---

## 18. Implementation Rules for the Coding Agent

When implementing this plan:

1. Read the relevant existing code before editing.
2. Prefer extension hooks over core-file modifications.
3. Make one logical patch at a time.
4. Keep the Governor independently testable.
5. Do not introduce a second token-counting implementation unnecessarily.
6. Reuse existing artifact/screenshot/reference mechanisms where possible.
7. Never silently discard information needed for browser actions.
8. Store large information externally and provide a reference.
9. Make all budgets configurable.
10. Preserve current browser APIs unless a concrete gap is demonstrated.
11. Preserve Responses API behavior.
12. Do not optimize based on guessed token numbers; use provider/context measurements.
13. Do not disable vision globally as a shortcut.
14. Do not lower the global context window as the primary fix.
15. Do not rewrite `helpers/history.py` in Phase 1.
16. After implementation, compare benchmark results against `inno-baseline-0-v2.11`.

---

## 19. Recommended First Coding Task

The safest first patch is intentionally small:

```text
Patch A
------
Create Context Governor core + tests.

Patch B
------
Intercept browser tool results and convert oversized document results
into bounded observations + artifact references.

Patch C
------
Stop BrowserContextPrompt from injecting the full document and use
Governor-generated compact state.

Patch D
------
Add retrieval/escalation.

Patch E
------
Run browser automation benchmark and tune budgets.
```

This sequence gives a fast rollback point and isolates regressions.

---

## 20. Final Engineering Position

The current Agent Zero architecture already contains useful primitives: extension hooks, history compression, token estimation, context-window accounting, browser artifacts/screenshots, and provider usage reporting.

The customization should therefore be **surgical**, not a fork-wide rewrite.

The central principle for Inno Agent is:

> **Observe small. Store large. Retrieve on demand. Measure everything.**

This should make browser/social automation substantially more token-efficient while preserving Agent Zero's general-purpose capabilities.

---

## Source / Audit Input

This implementation plan is based on the repository audit output supplied for the Inno Agent customization project, including the browser context extension, browser tool result path, context-window usage subsystem, history compression path, and model configuration findings. fileciteturn20file0
