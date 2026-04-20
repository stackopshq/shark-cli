# ADR-0003: Auth-type auto-detection

**Status**: Accepted
**Date**: 2026-04-20

## Context

OpenStack Keystone v3 supports several authentication methods. orca needs
to handle at least `password` and `v3applicationcredential`. A user's
profile or env vars may contain credentials for both, especially after a
migration from password to application credential where the old
`password` is left behind.

Forcing the user to set an explicit `auth_type` field on every profile
adds friction and is error-prone (typos, missing key on import from
`clouds.yaml`).

## Decision

`OrcaClient` auto-detects the auth type from the *presence* of credential
fields, with **application credential taking precedence over password**:

1. If `auth_type` is explicit in config → use it as authoritative.
2. Else if any `application_credential_*` field is present → use
   `v3applicationcredential`.
3. Else → use `password`.

This matches OpenStack ecosystem conventions (`os-client-config`
behaviour) and means a profile that was migrated to AC keeps working
even if the legacy password was forgotten in the file.

## Consequences

- **Positive**: zero-config for the common case; explicit
  `auth_type: password` is still respected for users who want to override.
- **Positive**: profiles imported from `clouds.yaml` work without
  post-processing.
- **Negative / trade-off**: a stray `application_credential_id` left in a
  profile (e.g. half-edited) will silently switch the auth method. The
  user sees a Keystone "credential not found" error rather than a wrong-
  password error.
- **Mitigation**: `orca profile show` displays the resolved `auth_type`
  so the user can see which path will run.
