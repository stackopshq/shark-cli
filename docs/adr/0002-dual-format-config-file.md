# ADR-0002: Dual-format configuration file

**Status**: Accepted
**Date**: 2026-04-20

## Context

`~/.orca/config.yaml` originally held a single OpenStack profile as a
flat YAML document (`auth_url`, `username`, `password`, …). Multi-account
support required a richer schema with named profiles and an active-profile
marker. We had two options:

1. Migrate users on first read — overwrite the legacy file with the new
   shape — then only ever support the canonical schema.
2. Read both shapes forever, write the canonical shape going forward.

Option 1 is cleaner code but breaks every existing user's config the first
time the new orca runs in a non-interactive context (CI, scripts).

## Decision

`config.py::load_config` accepts both formats:

- **Canonical**: `{ active_profile: <name>, profiles: { <name>: {...} } }`
- **Legacy**: a flat dict with the credential keys at root level — treated
  as a single profile named `default`.

Writes always use the canonical format. The legacy reader is a transparent
adapter, never a destructive rewrite.

## Consequences

- **Positive**: zero-friction upgrade — pre-existing single-profile users
  see no behaviour change until they explicitly add a second profile.
- **Positive**: `tests/test_profile_convert.py` locks the legacy reader in
  place; any change to it must update those tests.
- **Negative / trade-off**: every config-touching code path has to go
  through `load_config` rather than reading the YAML directly, otherwise
  the legacy shape leaks into callers as raw dicts.
- **Negative / trade-off**: the dual-read path is permanent — there is no
  scheduled removal date. Removing it later means breaking those users
  who never wrote a profile.
