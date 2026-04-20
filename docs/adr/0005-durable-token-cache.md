# ADR-0005: Durable, atomic token cache

**Status**: Accepted
**Date**: 2026-04-20

## Context

OpenStack tokens expire after typically one hour. Without a cache, every
`orca` invocation triggers a fresh Keystone authentication round-trip
(50–300 ms over the wire) — multiplied by every CLI call in a script,
this dominates wall-clock time and hammers Keystone.

A naïve in-memory cache helps within one process but doesn't survive the
exit of a CLI command. Persisting the token to disk introduces real
concerns: file leak, write torn on signal, multi-process races.

## Decision

Tokens are persisted at `~/.orca/token_cache.yaml` with these invariants:

- **Filesystem mode `0600`** — readable only by the owning user.
- **Cache key** = SHA-256 of `auth_url|username|domain|project|region` —
  the cleartext components are not stored as the key.
- **Atomic write** — `tempfile.mkstemp()` in the target directory →
  `chmod 0600` → write contents → `os.replace()`. This guarantees the
  file is either the previous good state or the new good state, never
  half-written, and never world-readable for a window between create and
  chmod.
- **Expiry buffer** = 5 minutes. We treat a token as expired when its
  remaining lifetime drops below the buffer, so an in-flight request
  doesn't 401 mid-operation.
- **401 → wipe + re-auth once**. If the server still rejects after a
  fresh authentication, surface the error.

## Consequences

- **Positive**: subsequent commands within the token's lifetime skip
  Keystone entirely. Measured impact: 200–400 ms saved per invocation in
  a script that calls orca repeatedly.
- **Positive**: file mode 0600 + hashed key means a `cat token_cache.yaml`
  by another local user reveals nothing useful.
- **Negative / trade-off**: tokens *are* on disk. A compromise of the
  user's home directory grants the attacker the live token. We accept
  this — same posture as `~/.aws/credentials`, `~/.kube/config`, etc.
- **Negative / trade-off**: clock skew between the orca host and Keystone
  can cause the buffer to mis-fire. Workaround is `ntpd` / `chrony` —
  not orca's problem to solve.
