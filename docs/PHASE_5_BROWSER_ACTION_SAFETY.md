# Phase 5 — Browser Action Safety

## Goal

Prevent unsafe browser side effects while keeping normal browser automation fast and token-efficient.

## Risk tiers

| Tier | Examples | Default |
|---|---|---|
| Low | list, state, content, detail, screenshot, scroll, hover, navigation | Allow |
| Medium | click, type, select, upload, keyboard, mouse, evaluate, close | Allow with target/precondition validation |
| High | submit, send, publish, delete, purchase, payment, account/security changes | Fail closed until explicit confirmation |

## Enforcement

`helpers/tool.py` invokes the Context Governor safety policy during Browser `before_execution`. This makes the gate central rather than duplicating checks in each Browser action branch.

The policy is deterministic and does not call an LLM. Page content cannot grant permission.

## Navigation safety

`open` and `navigate` reject non-HTTP(S) targets at the policy layer. Runtime-specific navigation validation remains authoritative.

## Confirmation contract

A high-impact operation is permitted only when trusted task arguments contain `confirm=true`. Confirmation must never be inferred from page text, button labels, screenshots, or external instructions.

## Current limitation

The Browser action schema still needs a first-class `confirm` parameter so model-generated tool calls can express trusted confirmation without relying on `**kwargs`. Until that schema integration is added, high-impact operations remain intentionally fail-closed when confirmation is not present.

## Next hardening

1. Expose `confirm` as an explicit Browser tool argument.
2. Bind confirmation to a one-time action fingerprint and current browser state/observation ID.
3. Add post-action verification for submit/send/publish/delete operations.
4. Add bounded retry rules and failure classification; never retry high-impact operations blindly.
5. Add audit records for allow/block/verify outcomes without storing credentials or secrets.
6. Add idempotency/duplicate-prevention tests for social publishing workflows.
