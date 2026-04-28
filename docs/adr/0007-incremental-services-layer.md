# ADR-0007: Incremental services layer with typed models

**Status**: Accepted (migration complete 2026-04-28)
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
- 2026-04-22 — IdentityService extension: Keystone enforcement
  limits. Added ``find_registered_limits`` / ``get_registered_limit``
  / ``create_registered_limits`` (batched POST) / ``update_registered_limit``
  / ``delete_registered_limit`` and their project-scoped twins
  ``find_limits`` / ``get_limit`` / ``create_limits`` /
  ``update_limit`` / ``delete_limit``. TypedDicts: RegisteredLimit
  and Limit. Migrated ``commands/limit.py`` — the last ``_iam()``
  helper in the Keystone set is gone.
- 2026-04-22 — Final cross-service cleanup: routed every remaining
  direct ``client.get/post/put/delete`` call that targeted a ``*_url``
  with an existing service wrapper through that service. Touched
  ``commands/watch.py``, ``audit.py``, ``ip_whois.py``, ``cleanup.py``
  (dropped the dead ``_collect`` helper), ``project.py`` (same),
  ``overview.py``, ``export.py``, ``find.py`` (dropped the dead
  ``_safe_list`` helper), ``network.py`` (topology + trace server
  lookups). Only documented exceptions keep direct ``client.*``:
  health probes in ``doctor.py``, Swift binary streaming + account
  metadata POST in ``object_store.py``, Designate text/dns import/
  export in ``zone.py``, Barbican text/plain payload GET in
  ``secret.py``, Placement single-inventory GET + bulk DELETE-all in
  ``placement.py``, and the auth flow in ``auth.py``.
- 2026-04-22 — ``quota`` (cross-service): no dedicated service; the
  ``orca quota`` command routes each slice through its owning service
  — ``ComputeService.get_limits`` (Nova), a new
  ``VolumeService.get_limits`` (Cinder absolute limits), and new
  ``NetworkService.find_quotas`` / ``get_quota`` (Neutron), with the
  Neutron usage counts going through the existing ``find_*`` methods.
- 2026-04-22 — ``placement``: PlacementService + ResourceProvider /
  Inventory / ProviderUsages / ResourceClass / Trait / Allocation /
  AllocationCandidate TypedDicts. Resource providers (CRUD),
  inventories, usages (per-provider + per-project), resource classes,
  traits (global + per-provider), allocations per consumer, allocation
  candidates, provider aggregates. Service owns the
  ``OpenStack-API-Version: placement 1.6`` header. Migrated
  ``commands/placement.py`` — the ``_url()`` and ``_ph()`` helpers
  are gone. Single-inventory GET + bulk DELETE-all inventories keep
  direct ``client.*`` calls (no service methods for them yet).
- 2026-04-22 — ``container-infra`` (Magnum): ContainerInfraService +
  Cluster / ClusterTemplate / NodeGroup TypedDicts. Clusters (CRUD +
  JSON Patch update with ``application/json-patch+json`` + upgrade
  action), cluster templates (CRUD), node groups per-cluster (CRUD +
  JSON Patch update). Migrated ``commands/cluster.py`` — the
  ``_magnum()`` helper is gone.
- 2026-04-22 — ``telemetry`` (Gnocchi metric + Aodh alarm + Nova
  instance-actions): MetricService, AlarmService, and new
  ``find_instance_actions``/``get_instance_action`` methods on
  ServerService. Shared TypedDicts in ``models/telemetry.py``
  (GnocchiResource / GnocchiMetric / ArchivePolicy /
  GnocchiResourceType / Alarm / AlarmHistoryEntry). Migrated
  ``commands/metric.py`` (drops ``_gnocchi()``),
  ``commands/alarm.py`` (drops ``_url()``, keeps fetch-merge-put
  on ``alarm set``), ``commands/event.py`` (drops direct
  ``client.compute_url``, routes through ServerService).
- 2026-04-22 — ``rating`` (CloudKitty): RatingService + RatingModule
  / HashmapService / HashmapField / HashmapMapping / HashmapThreshold
  / HashmapGroup / RatingSummary TypedDicts. Info (config + metrics),
  summary + dataframes (v1/v2), quotes, rating modules (fetch-merge-
  put on ``module set``), hashmap sub-API
  (services/fields/mappings/thresholds/groups). Migrated
  ``commands/rating.py`` — the ``_url()`` helper and the duplicated
  hashmap prefix constant are gone.
- 2026-04-22 — ``key-manager`` (Barbican): KeyManagerService + Secret
  / SecretContainer / Order / Acl TypedDicts. Secrets, secret ACLs,
  secret containers, orders. Migrated ``commands/secret.py`` (drops
  ``_barbican()`` helper, consolidates ``secret_ref`` UUID extractor)
  and the secret branch in ``project.py``. The raw text/plain
  ``secret get-payload`` keeps its ``client._http`` call — the
  service exposes JSON-bodied methods only.
- 2026-04-22 — ``dns`` (Designate): DnsService + Zone / Recordset /
  ZoneTransferRequest / Tld TypedDicts. Zones CRUD, recordsets CRUD
  (per-zone + cross-zone), export/import tasks, transfer requests +
  accepts, reverse-PTR floating-ip lookup, TLDs. Migrated
  ``commands/zone.py``, ``commands/recordset.py`` (both drop local
  ``_dns()`` helpers), plus the dns-zone branches in ``project.py``
  cleanup + ``_delete_one``. Zone export/import that streams raw
  text/dns bodies still uses ``client._http`` directly.
- 2026-04-22 — ``object-store`` (Swift): ObjectStoreService +
  Container / ObjectEntry TypedDicts. Account/container/object CRUD,
  HEAD metadata reads, POST metadata writes (with full-name header
  keys), and an ``object_url(container, name)`` helper for streaming
  upload/download. Migrated ``commands/object_store.py`` and
  ``commands/container.py`` (dropped the local ``_head`` /
  ``_post_no_body`` / ``_swift`` helpers), plus the Swift container
  branch of ``commands/project.py`` cleanup. Binary up/download still
  uses ``client._http`` directly (streaming), which is intentional —
  the service provides the URL only.
- 2026-04-22 — ``load-balancer`` (Octavia): LoadBalancerService +
  LoadBalancer / Listener / Pool / Member / HealthMonitor / L7Policy
  / L7Rule / Amphora TypedDicts. Migrated ``commands/loadbalancer.py``
  (lb CRUD + stats + status, listeners, pools + members, health
  monitors, L7 policies + rules, admin amphorae + failover) and the
  cross-service Octavia callers in ``commands/cleanup.py``,
  ``commands/project.py`` and ``commands/ip_whois.py``.
- 2026-04-22 — ``orchestration`` (Heat): OrchestrationService + Stack /
  StackResource / StackEvent / StackOutput TypedDicts. Migrated
  ``commands/stack.py`` (stack CRUD + actions + abandon; resources,
  events, outputs, templates, validate, resource types) and the
  Heat callers in ``commands/cleanup.py`` (failed-stack discovery +
  delete) and ``commands/project.py`` (project cleanup + _delete_one
  stack branch).
- 2026-04-22 — ``identity`` (Keystone v3): IdentityService + Project /
  User / Role (+ RoleAssignment / RoleInference) / Domain / Group /
  Credential / ApplicationCredential / Endpoint / EndpointGroup /
  Service / Region / Policy / IdentityProvider / FederationProtocol /
  Mapping / ServiceProvider / Trust / AccessRule TypedDicts.
  Migrated 16 command modules: project, user, role (+ grants +
  assignments + implied roles), domain, group (+ membership),
  credential, application_credential, endpoint, endpoint_group
  (+ project attachments), service, region, policy, federation
  (identity-provider/protocol/mapping/service-provider, PUT upsert),
  trust (immutable; no update method), token (revoke only; ``issue``
  stays on cached token state), access_rule (read-only per-user).
  The service preserves the historical split between callers that
  prepend ``/v3`` to ``client.identity_url`` and callers that use it
  directly (credentials, endpoints, services, regions, OS-TRUST).
  Cross-service Keystone lookups in ``commands/project.py cleanup``
  (project-by-name / project-by-id resolution) route through
  IdentityService too. ``commands/catalog.py`` still reads
  ``client._catalog`` from the auth token state — no HTTP call.
- 2026-04-22 — ``compute`` (Nova, non-server): ComputeService + Flavor
  (+ FlavorAccess) / Keypair / Aggregate / Hypervisor (+ statistics) /
  AvailabilityZone / ComputeService / ServerGroup / TenantUsage /
  AbsoluteLimits TypedDicts. Eight command modules migrated:
  ``commands/flavor.py`` (incl. extra-specs + tenant-access actions),
  ``commands/keypair.py``, ``commands/aggregate.py`` (incl. add/remove
  host, set/unset metadata, cache-image), ``commands/hypervisor.py``
  (list/show/statistics/usage ranking), ``commands/availability_zone.py``,
  ``commands/compute_service.py``, ``commands/server_group.py``,
  ``commands/usage.py``, ``commands/limits.py`` (absolute),
  ``commands/quota.py`` (Nova portion). Cross-service ``os-keypairs``
  callers in ``overview.py``, ``export.py``, ``find.py`` route through
  ComputeService. ServerService stays the owner of ``/servers``.
- 2026-04-22 — ``network``: NetworkService + Network / Subnet / Port /
  Router / FloatingIp / SecurityGroup (+ SecurityGroupRule) /
  SubnetPool / Trunk (+ TrunkSubPort) / QosPolicy (+ QosRule) / Agent
  / RbacPolicy / Segment / AutoAllocatedTopology TypedDicts. All six
  Neutron command modules (``commands/network.py`` with 50+ subcommands
  — networks, subnets, ports, routers with add/remove/set/unset
  subgroups, agents, RBAC, segments, auto-allocated-topology, plus
  topology/trace diagnostics; ``commands/floating_ip.py``,
  ``commands/security_group.py``, ``commands/subnet_pool.py``,
  ``commands/trunk.py``, ``commands/qos_policy.py``) now go through
  the service. Cross-service Neutron fetches in ``commands/overview.py``,
  ``commands/export.py``, ``commands/cleanup.py``, ``commands/find.py``
  and ``commands/project.py`` (incl. the router interface detach loop
  before delete) route through NetworkService too. Only non-Neutron
  callers (Nova os-keypairs, Cinder, Heat, Octavia, Swift, Designate,
  Barbican) keep direct ``client.*`` calls until their respective
  services land.
- 2026-04-28 — Final migration sweep, ADR-0007 reaches 100 %:
  - ``auth.token-revoke`` routed through the existing
    ``IdentityService.revoke_token``.
  - PlacementService gains ``get_inventory`` (single resource_class
    GET) and ``delete_all_inventories`` (bulk DELETE); the two
    remaining holdouts in ``commands/placement.py`` are gone.
  - Streaming I/O is now expressed in services. ``OrcaClient`` exposes
    ``put_stream`` (rewritten — explicit ``content_length``, no retry
    because streamed bodies cannot be replayed), ``post_stream``,
    ``post_no_body``, ``head_request``, and ``get_stream`` with
    ``extra_headers``. ObjectStoreService gains ``upload_object`` /
    ``download_object`` / ``fetch_object_bytes`` /
    ``post_account_metadata``. ImageService.upload/stage now take a
    ``content`` iterable and an optional ``content_length``.
    DnsService gains ``fetch_export_text`` /
    ``import_zone_text`` for the Designate text/dns endpoints.
    KeyManagerService gains ``get_secret_payload`` for the Barbican
    text/plain endpoint.
  - The auth-state attributes commands previously read off the client
    (``_token``, ``_token_data``, ``_catalog``, ``_auth_url``,
    ``_region_name``, ``_interface``, ``_project_id``) are now public
    properties on ``OrcaClient``. ``_authenticate()`` is exposed as
    ``authenticate()``.
  - ``orca doctor`` reachability probes and quota checks route through
    Compute / Volume / Network / Image services.
    ``NetworkService.get_quota_details`` covers the
    ``/quotas/{id}/details`` endpoint that was missing.
  - **BackupService + models/backup.py introduced**: 24 Freezer
    operations (backups, jobs, sessions, clients, actions) finally
    have a service. ``commands/backup.py`` no longer issues raw HTTP.
  - A ratchet test
    (``tests/test_no_private_client_api_in_commands.py``) walks every
    command module and fails if a future change reintroduces
    ``client._<anything>``.
  - Result: zero ``client.get/post/put/patch/delete`` and zero
    ``client._*`` accesses remain in ``orca_cli/commands/``. Every
    command module is service-only.
