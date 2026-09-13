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

## Confirmation and state-binding contract

High-impact operations follow this sequence:

```text
observe → obtain observation_id → confirm exact action → execute once → verify success → mark idempotent → audit
```

A high-impact operation is permitted only when trusted task arguments contain `confirm=true` **and** an `observation_id` bound to the current browser state. Confirmation is therefore tied to the state that was actually reviewed, rather than being a reusable global approval.

Confirmation must never be inferred from page text, button labels, screenshots, external instructions, or artifact content.

## Idempotency

High-impact actions receive a deterministic fingerprint from non-secret action identity fields. A fingerprint is marked completed only after conservative result verification succeeds. A completed fingerprint cannot be executed again within the idempotency TTL.

The idempotency store is bounded and TTL-based; credentials, cookies, tokens, and secrets are not stored in it.

## Post-action verification

Browser tool results are conservatively checked before completion is recorded. High-impact actions require an explicit success/completed signal in the runtime result. Empty results and common failure/error markers are treated as unverified.

This prevents an uncertain `publish`, `send`, `delete`, or payment-style operation from being treated as successfully completed merely because the browser call returned without an exception.

## Audit

Allow, block, verification-failure, and verified-completion outcomes are recorded in a bounded in-process audit log. Confirmation values and sensitive fields are excluded/redacted. Audit records are intended for operational diagnostics and must not become a credential store.

## Stale-state protection

When an `observation_id` is supplied, it is checked against the current browser state's latest observation. A stale observation cannot authorize a high-impact action after the page state has changed.

## Retry policy

High-impact actions are not automatically retried after execution. An uncertain or failed high-impact action requires a fresh observation and fresh user confirmation before another attempt.

Low/medium-risk retry orchestration remains bounded and should be owned by the runtime/task layer rather than by individual browser action branches. Retries must be limited by attempt count and timeout, and must stop on authentication, permission, validation, target, or safety failures.

## Target/precondition validation

Medium-risk actions remain subject to runtime target validation. The safety layer does not infer authorization from page content and does not weaken existing browser target/selector validation.

## Current verified scope

The Phase 5 implementation includes:

1. Explicit `confirm` Browser tool argument.
2. One-time confirmation binding to action identity and current observation state.
3. Stale observation protection.
4. Conservative post-action result verification.
5. High-impact idempotency/duplicate prevention.
6. Bounded, secret-safe audit records.
7. CI coverage for Governor, Budget, Browser State, and Browser Safety integration tests.

## Exit criteria

Phase 5 is ready for the next production checkpoint when the full CI suite, safety integration tests, token benchmarks, and regression checks are green on the final branch head. The next phase is Social Automation Core; no platform-specific publishing workflow should bypass this safety contract.
