# Architecture Decision Records

This folder records the *non-obvious* design decisions behind orca — the
choices a future contributor would otherwise have to reverse-engineer from
the code, and where a casual refactor could silently undo a deliberate
trade-off.

ADRs are intentionally short (one page each). Format:

```
# ADR-NNNN: Title

**Status**: Accepted | Superseded by ADR-MMMM | Deprecated
**Date**: YYYY-MM-DD

## Context
What problem we faced.

## Decision
What we chose to do.

## Consequences
- Positive: ...
- Negative / trade-off: ...
```

When a decision is reversed, *don't delete the ADR* — mark it
`Superseded by ADR-MMMM` and add a new file. The history of choices is part
of the documentation.

## Index

- [ADR-0001 — Lazy command registration](0001-lazy-command-registration.md)
- [ADR-0002 — Dual-format configuration file](0002-dual-format-config-file.md)
- [ADR-0003 — Auth-type auto-detection](0003-auth-type-auto-detection.md)
- [ADR-0004 — No services layer (yet)](0004-no-services-layer.md) *(superseded by ADR-0007)*
- [ADR-0005 — Durable, atomic token cache](0005-durable-token-cache.md)
- [ADR-0006 — Idempotent-only HTTP retries](0006-idempotent-only-retries.md)
- [ADR-0007 — Incremental services layer with typed models](0007-incremental-services-layer.md)
- [ADR-0008 — Command naming follows openstackclient convention](0008-command-naming-convention.md)
- [ADR-0009 — Server boot mode defaults to boot-from-image](0009-server-boot-mode-policy.md)
