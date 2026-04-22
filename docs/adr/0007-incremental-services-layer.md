# ADR-0007: Incremental services layer with typed models

**Status**: Accepted
**Date**: 2026-04-20
**Supersedes**: [ADR-0004](0004-no-services-layer.md)

## Context

ADR-0004 deferred the services layer because the cost of refactoring all
63 command modules at once was disproportionate to the immediate gain.
Two months later the friction it predicted has materialised:

- 740-odd raw `client.get/post/...` calls scattered across commands made
  the recent N+1 hunt (cleanup, watch, export) harder than it should
  have been: each fix had to be re-derived from the URL string.
- The `dict[str, Any]` access pattern (2 136 `.get()` calls) means
  `srv.get("nmae", "")` typos slip through to runtime; mypy can't help
  because everything is `Any`.
- Tests mock at the `OrcaClient` boundary; they assert on the URL string
  passed to `client.get`. Renaming an endpoint or changing pagination
  scheme breaks the assertions in cosmetic ways.

The original concern — multi-day refactor with high regression risk —
remains valid only if we attempt the migration in one shot.

## Decision

Introduce two new layers, **incrementally, one resource at a time**:

- `orca_cli/models/<resource>.py` — `TypedDict`s describing the subset
  of each Nova/Cinder/Neutron/etc. payload that orca actually reads.
  `total=False` everywhere — fields are added as commands need them.
- `orca_cli/services/<resource>.py` — a class wrapping `OrcaClient` that
  exposes typed methods (`list`, `get`, `delete`, `reboot`, ...) and
  owns the URL construction for that resource.

Migration order is driven by pain, not by alphabetical resource name.
The first migration is `server` (66 raw HTTP calls, 2235 LOC, the most
exercised module). Each migration ships as one commit per command being
refactored, never a "rewrite the whole module" PR. Commands that haven't
been migrated keep calling `OrcaClient` directly — there is no flag day.

The criteria for *not* introducing a service for a given resource:

- Single-call wrapper (`get_token`, `get_catalog`) where the service
  would just be a one-liner over the client. Stay direct.
- Resource that orca only reads, never writes, with one or two calls
  total. The service overhead exceeds the gain.

## Consequences

- **Positive**: typed return values mean autocomplete, mypy catches
  field-name typos, and refactors propagate to compile-time errors.
- **Positive**: URL construction lives in one place per resource; an
  OpenStack version bump touches `services/<resource>.py`, not 30
  command handlers.
- **Positive**: tests can assert on `service.list.return_value =
  [<typed Server>]` rather than mocking `client.get` URL-strings.
  Less brittle, more readable.
- **Negative / trade-off**: the codebase has *two* patterns for several
  weeks (or months) until every resource is migrated. The boundary is
  visible — a command either imports `services.X` or calls `client.get`
  directly. We accept the ugliness; a flag-day rewrite was the
  alternative we already rejected.
- **Negative / trade-off**: `TypedDict` doesn't enforce field presence
  at runtime — `srv["status"]` still raises `KeyError` if missing. The
  contract is "*if* this field exists, *then* it has this type". For
  presence guarantees we'd need `dataclass` + factory functions; that
  conversion can come later if the runtime safety pays off.

## Migration tracking

When migrating a resource, leave a one-line entry below so future ADR
readers can see how far along the work is.

- 2026-04-20 — `server`: ServerService + Server TypedDict introduced.
  All 59 server subcommands now go through the service for compute API
  calls. Five `client.*` calls remain in `commands/server.py`: four
  cross-service (Glance image lookup, Cinder volume lookup, Cinder
  snapshot create, used by `ssh user-detection` / `clone` / `snapshot`)
  to migrate when ImageService and VolumeService land, plus one bulk
  `PUT /servers/{id}/tags` call (the service exposes per-tag add/delete
  operations only).
- 2026-04-20 — `volume`: VolumeService + Volume / VolumeSnapshot /
  VolumeBackup / VolumeAttachment TypedDicts. All 71 subcommands now
  go through the service. Remaining ``client.volume_url`` references
  in commands/volume.py are URLs passed to ``wait_for_resource`` —
  not HTTP calls. Service covers volumes, snapshots, backups,
  attachments, types (+ access + extra-specs), QoS, transfers,
  messages, groups, group snapshots, group types, services.
- 2026-04-22 — `image`: ImageService + Image / ImageMember / ImageTask
  / ImageStore TypedDicts. All 24 ``orca image`` subcommands go through
  the service (CRUD, upload/stage/download streaming, deactivate/
  reactivate, tags, members/sharing, import API, cache admin, multi-
  backend stores info, async tasks). Cross-service Glance lookups in
  ``commands/server.py`` (SSH user detection), ``commands/overview.py``,
  ``commands/export.py``, ``commands/project.py`` (purge + delete) and
  ``commands/find.py`` (universal search) now route through
  ImageService too. Only ``commands/doctor.py`` keeps a raw
  ``client.image_url`` reference — it is an intentional health-probe
  URL, not a business call.
- 2026-04-22 — Residual cleanups on migrated resources: added
  ``ServerService.set_tags`` / ``delete_all_tags`` to cover the bulk
  ``PUT /servers/{id}/tags`` replacement (previously the only remaining
  direct ``client.put`` in ``commands/server.py``), and routed the
  ``volume tree`` server-name lookup through ``ServerService.find``
  instead of a direct ``/servers/detail`` call.
