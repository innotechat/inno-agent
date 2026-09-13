# Social Automation Core

Platform-independent social workflow layer for Agent Zero.

## Design

```text
Intent → Account → Capability → Draft → Approval → Execution → Verify → Audit
                         │
                         └── platform adapter
                                      │
                              Browser/API runtime
```

The core deliberately does not depend on DOM structure, screenshots, cookies, credentials, or provider-specific selectors. Platform adapters own those details.

## Safety Contract

- Publishing requires explicit approval by default.
- Automatic publishing is disabled by default.
- Draft validation happens before approval.
- Duplicate publishes are blocked with an idempotency key.
- LLM-facing execution context contains identifiers and state, not full page content.
- Credentials must never be placed in social models, fingerprints, or audit records.
- Browser execution must still pass the Phase-5 Browser Action Safety gate.

## Planned adapters

LinkedIn, X, Facebook, Instagram, and other providers should implement `SocialPlatformAdapter` independently. Browser automation is an adapter/runtime concern, not part of the social domain model.
