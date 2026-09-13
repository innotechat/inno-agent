# Phase 6 — Social Automation Core

## Goal

Provide a platform-agnostic social automation layer that separates social intent and workflow state from browser/API execution.

## Architecture

```text
Social Task
    ↓
SocialAutomationCore
    ↓
Platform Adapter
    ↓
Browser/API Runtime
    ↓
Phase-5 Safety Contract
    ↓
Verify + Audit
```

The core must not know DOM selectors, browser mechanics, cookies, credentials, or platform-specific UI details.

## Initial domain

- `SocialAccount`: platform, account/profile identity, capabilities.
- `SocialDraft`: text/media references and approval state.
- `SocialAction`: explicit operation with account, draft, target, and idempotency key.
- `SocialPlatformAdapter`: platform-specific capability, validation, draft, and publish contract.

## Approval state machine

```text
DRAFT → PENDING → APPROVED → PUBLISHED
          │
          └────→ REJECTED

APPROVED → FAILED
```

Publishing is never allowed directly from `DRAFT` or `PENDING`.

## Safety boundary

Phase 5 remains authoritative for browser side effects. Social Core does not bypass browser safety, confirmation, stale-state protection, verification, or audit controls.

## Token-efficiency rules

1. Core objects contain compact identifiers and references rather than raw browser documents.
2. Media is represented by `media_refs`; binary content does not enter the social action context.
3. Platform adapters own platform-specific observation and execution.
4. Browser DOM is retrieved only when an adapter needs it for a concrete action.
5. Draft generation and browser execution remain separate stages.

## Idempotency

Publish actions require an idempotency key. A successful key cannot be published again by the same core instance.

The core does not store credentials or raw browser session data.

## Current checkpoint

Implemented in the Phase 6 branch:

- platform-neutral models
- adapter interface
- draft creation and validation
- approval/rejection state transitions
- publish gate
- duplicate publish protection
- offline fake-adapter tests
- dedicated CI workflow

## Next checkpoint

Add a capability-aware execution contract and a first platform adapter using the existing Phase-5 browser safety boundary. Real publishing remains approval-gated.
