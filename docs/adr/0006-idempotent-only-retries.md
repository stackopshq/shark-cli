# ADR-0006: Idempotent-only HTTP retries

**Status**: Accepted
**Date**: 2026-04-20

## Context

OpenStack APIs occasionally return transient `5xx` responses or fail with
network errors that resolve on a second try. Generic HTTP-client retry
policies often retry every request, including `POST` and `PATCH`. For an
*infrastructure* CLI, that is dangerous:

- A `POST /servers` that succeeded server-side but lost the response on
  the network would, on retry, create a second server — silent
  duplication, billable.
- A `PATCH` that partially applied could compose with itself in
  unpredictable ways depending on the operation semantics.

## Decision

`OrcaClient._request` retries **only idempotent methods**:
`GET`, `HEAD`, `OPTIONS`, `PUT`, `DELETE`. `POST` and `PATCH` are never
retried automatically — a transient failure surfaces as an error to the
user, who decides whether re-running the command is safe.

Retry policy:

- Up to `MAX_RETRIES = 2` attempts after the initial one.
- Triggered by `httpx` connect/read timeouts, `httpx.NetworkError`,
  and HTTP `500/502/503/504`.
- Exponential backoff with jitter: `random.uniform(0, base * 2**attempt)`.
- `429` (rate-limit) is handled separately, honouring `Retry-After`
  per RFC 7231 with a `MAX_RATE_LIMIT_WAIT = 60s` cap.

## Consequences

- **Positive**: no risk of duplicated `POST`-side resource creation.
- **Positive**: aligns with HTTP RFC 7231 §4.2.2 semantics — operations
  that the protocol *defines* as idempotent get the safety net; the rest
  don't.
- **Negative / trade-off**: a transient blip during `POST /servers` will
  surface as an error even though re-running might succeed. Users have
  to make the call themselves. Documented in `--help`.
- **Invariant to protect**: any future change to `_request` must
  preserve `is_idempotent = method.upper() in {"GET","HEAD","OPTIONS","PUT","DELETE"}`.
  A reviewer adding `POST` to the retry set has to update this ADR
  *and* explain why duplicates are now acceptable.
