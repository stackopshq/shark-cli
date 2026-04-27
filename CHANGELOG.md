# Changelog

All notable changes to orca are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.2] — 2026-04-27

### Fixed

- **`volume upload-to-image` was unusable on older Cinder
  microversions.** The action body sent `visibility` and `protected`
  unconditionally, even when the user accepted the Click defaults
  (`private` / `False`). Older Cinder builds (e.g. some shipping
  microversions still in production at large public-cloud operators)
  reject the request with HTTP 400 — *Additional properties are not
  allowed ('protected', 'visibility' were unexpected)* — because
  those fields were added in a later microversion. Both flags are
  now opt-in: omitted from the JSON body unless the user passes one
  explicitly, in which case the value is forwarded verbatim. Glance
  applies its own server-side defaults when the keys are absent, so
  modern clouds see no behavioural change. `--disk-format` and
  `--container-format` keep their hard-coded defaults — those are
  stable across every Cinder microversion.

## [2.1.1] — 2026-04-27

### Added

- **`orca volume upload-to-image`** — materialize a Cinder volume as a
  downloadable Glance image (wraps the `os-volume_upload_image` action).
  This is the missing primitive for migrating boot-from-volume instances
  between clouds: `orca server image create` on a BFV server only produces
  a 0-byte Glance shell that points at a Cinder snapshot, whereas the new
  command yields a self-contained image that `orca image download` can
  actually pull. Supports `--disk-format`, `--container-format`,
  `--visibility`, `--protected`, `--force` (required for in-use volumes,
  with a client-side pre-flight so users get an actionable message instead
  of an opaque 400), `--property KEY=VALUE` (validated against Glance's
  schema and applied via JSON-Patch on the resulting image, since Cinder
  itself does not accept arbitrary properties in the action body), and
  `--wait` (adaptive polling: 5 s for the first minute, then 15 s, with a
  live status/size line and an early exit on `killed`/`deleted`). The
  `--help` of `orca server image create` and `orca image download` now
  cross-reference the new workflow so the BFV pitfall is discoverable
  from both ends. ADR-0008 records `volume upload-to-image` as a
  permanent compound-verb exception (mirrors the Cinder action name).

## [2.1.0] — 2026-04-27

### Added

- **Full image-property support across `image create`, `image update` and
  `image show`.** Custom Glance properties (`os_distro`, `os_version`,
  `hw_qemu_guest_agent`, `cinder_img_volume_type`, …) can now be set on
  creation (`--property KEY=VALUE`, repeatable) and edited atomically on
  existing images (`--property` and `--remove-property`, `--ignore-missing`
  for idempotent removal). Property keys are validated client-side against
  Glance's `^[A-Za-z0-9_:.\-]{1,255}$` schema before any HTTP round-trip,
  and only the first `=` splits the value so URL-like values survive intact
  (`--property url=https://x?a=1&b=2`). `image show` surfaces every custom
  key Glance returns plus the integrity fields (`checksum`, `os_hash_algo`,
  `os_hash_value`, `direct_url`, `tags`): as a `Properties` sub-table in
  table format, under a new top-level `"properties"` aggregate in JSON
  (with each custom key **also** mirrored at the JSON root for backward
  compatibility — `jq .os_distro` keeps working alongside the new
  `jq .properties.os_distro`), and as `KEY VALUE` lines in value format.
  This unblocks lossless inter-cloud image migration.

### Fixed

- **Shell completion install no longer slows shell startup.** The
  bash/zsh install used to append
  `eval "$(_ORCA_COMPLETE=bash_source orca)"` to the rc file, which
  re-spawned `orca` (with its full ~60-module command tree) and a
  `bash --version` subprocess on every login (Click's
  `_check_version()`). Real-world cost was 1–3 s per shell, with a
  documented incident where hundreds of `orca` processes piled up on
  a single SSH session. `orca completion install bash` (and `zsh`)
  now generates the completion script **once** into
  `$XDG_DATA_HOME/orca/completion.<shell>` and writes a plain
  `source <path>` line into the rc — login cost drops to microseconds.
  Re-running the install on an older config silently migrates the
  legacy `eval` line out of the rc. See ADR 0010.

## [2.0.1] — 2026-04-22

### Fixed

- **Shell tab-completion triggered a fresh Keystone auth every 30 s.**
  The completion cache TTL was 30 seconds, so on an active terminal
  where the user kept typing, most tab presses after the first 30 s
  fell back to a cold fetch (auth + HTTP list). Extended the TTL to
  5 minutes — completion data (server names, flavor IDs, region
  lists) changes slowly and the old short TTL made the tab key feel
  sluggish.
- **Region completion mixed results across profiles.** The
  ``--region`` completion callback cached every region list under
  the same ``default_regions.json`` file regardless of
  ``--profile`` / ``ORCA_PROFILE``, so a user with several profiles
  pointing at different clouds saw the other cloud's regions. The
  callback now resolves the active profile and caches per-profile
  (``<profile>_regions.json``), matching the behaviour of the other
  completion callbacks in ``orca_cli/core/completions.py``.

## [2.0.0] — 2026-04-22

### Changed

- **Service layer completed.** Every OpenStack resource orca talks to
  now routes through a typed ``*Service`` class in ``orca_cli/services/``
  instead of constructing endpoint URLs in the command modules.
  Thirteen services land in this release — ``NetworkService``
  (Neutron), ``ComputeService`` (Nova non-server),
  ``IdentityService`` (Keystone, including enforcement limits),
  ``OrchestrationService`` (Heat), ``LoadBalancerService`` (Octavia),
  ``ObjectStoreService`` (Swift), ``DnsService`` (Designate),
  ``KeyManagerService`` (Barbican), ``RatingService`` (CloudKitty),
  ``MetricService`` + ``AlarmService`` (Gnocchi + Aodh),
  ``ContainerInfraService`` (Magnum), ``PlacementService``, plus the
  existing ``ServerService`` / ``VolumeService`` / ``ImageService``.
  Each service exposes ``find`` / ``get`` / ``create`` / ``update`` /
  ``delete`` methods and returns TypedDicts from ``orca_cli/models/``
  so mypy catches field-name typos at check time. ADR-0007 is updated
  per resource. Behaviour is unchanged — retry, auth, pagination still
  live in ``OrcaClient``. This is a surface-level reorganisation of
  the codebase; the CLI surface is identical.

### Fixed

- **Silent 1000-item cap in batch commands.** ``orca project cleanup``
  and ``orca server bulk {stop,delete,reboot}`` called
  ``ServerService.find(limit=1000)`` and silently dropped extra rows
  on tenants with more than 1000 servers — the batch operation
  reported success while leaving resources behind. Every such call
  now uses ``find_all()`` with full pagination. Also applied to the
  server-name-resolution side calls in ``orca volume tree``,
  ``orca network topology`` / ``trace``, ``orca ip-whois`` and
  ``orca event``.

## [1.4.0] — 2026-04-20

### Security

- **Visible warning when TLS verification is off.** Running with
  `insecure=true` now emits an explicit stderr warning on every
  invocation. Previously the flag was silent — the risk was invisible.
- **Validate the `cacert` path at startup.** A profile that points at a
  missing or unreadable CA bundle now fails with `ConfigurationError`
  (mentioning the path) instead of surfacing a cryptic TLS handshake
  error on the first request.
- **Pin `pypa/gh-action-pypi-publish` to an immutable commit SHA**
  (`cef22109…`, v1.14.0) rather than the mutable `release/v1` tag. The
  publish job has `id-token: write`, so an upstream action compromise
  could otherwise inject code into the release pipeline.

### Fixed

- **Token cache no longer subject to torn writes.** `_save_token_cache`
  writes to a sibling tempfile with mode 0600, then `os.replace`s it
  into place atomically. Two concurrent `orca` invocations racing on a
  re-authentication can no longer leave the cache half-written for the
  next reader.

### CI

- `ci.yml` caches pip and `.venv` (keyed on `pyproject.toml`), adds a
  `build` job that runs `poetry build` + publishes the dist artifacts,
  and a `security` job that runs `gitleaks` and `pip-audit` against the
  installed runtime deps.
- `deploy-docs.yml` is gated on the CI workflow succeeding on `main`
  (via `workflow_run` + `conclusion == 'success'`) so a failing build
  can no longer ship stale documentation.

## [1.3.0] — 2026-04-20

### Added

- `OrcaClient.paginate(url, key, ...)` walks OpenStack marker-based
  pagination to completion. `audit`, `overview`, `cleanup`, `export` and
  their lookup maps now use it instead of a bare `limit=1000`.
- `safe_output_path()` and `safe_child_path()` in `core/validators`:
  refuse to overwrite existing symlinks, and refuse API-derived child
  names that resolve outside a base directory (`..` traversal in bulk
  downloads). Applied to every command that writes a user-supplied path.
- Global `--debug` flag (also `ORCA_DEBUG=1`) wires an `orca_cli` logger
  to stderr. Logs auth intent (URL / user / project — not the payload),
  token-cache hits, each HTTP request (method, URL, redacted headers,
  status, duration) and retry decisions.
- `APIError.request_id` now carries the OpenStack `x-openstack-request-id`
  (or Nova's `x-compute-request-id`) when the service returns one. The id
  is also appended to the error message so an operator can correlate
  failures with back-end logs. Same treatment for `PermissionDeniedError`.
- `ProfileNotFoundError` and `ProfileConflictError` exceptions (both
  subclass `ConfigurationError`).

### Fixed

- **Silent data loss in batch commands.** `audit` / `overview` / `cleanup` /
  `export` passed `limit=1000` to Nova/Cinder/Neutron without paginating,
  so any tenant with more than 1000 of a given resource had rows dropped
  with no indication.
- **Symlink-race on file outputs.** Writing `orca export -o link.yaml`
  to a pre-existing symlink followed the link and clobbered the target.
  Fixed across `export`, `image download`, `container save`,
  `object download` / `container-save`, `keypair create`, `zone export`,
  `stack abandon`, `profile to-openrc` / `to-clouds`.
- **429 Too Many Requests failed immediately.** The retry loop honours
  `Retry-After` (RFC 7231 seconds or HTTP-date), capped at 60s before
  surfacing the error. 429 retries on any method including POST/PATCH —
  rate-limited requests are not processed, so re-sending is safe.
- **Thundering-herd retries.** 5xx and transient-network backoff now uses
  full jitter (`random.uniform(0, base * 2**attempt)`) so parallel CLI
  invocations in a CI runner don't retry in lockstep.

### Changed

- `core/config.py` profile mutations raise `ProfileNotFoundError` /
  `ProfileConflictError` instead of stdlib `KeyError` / `ValueError` —
  these now format through the CLI's top-level error handler like every
  other `OrcaCLIError`.
- `core/shell_completion.py::install_completion` raises `OrcaCLIError`
  instead of `ValueError` on an unsupported shell.

### Security

- TLS warning + Retry-After cap are guards against denial-of-service by
  a misbehaving upstream. No secrets were leaked in any prior release.

## [1.2.0] — 2026-04-20

### Added

- `orca completion install [shell]` auto-installs shell completion:
  bash/zsh append an idempotent `eval` line to the rc file, fish writes
  `~/.config/fish/completions/orca.fish`. Auto-detects `$SHELL` when the
  argument is omitted.
- `orca setup` offers to auto-install shell completion at the end of the
  wizard, then validates the just-saved profile against Keystone so typos
  surface immediately. Both steps are skipped in non-TTY contexts.
- `orca profile list` gains an `Auth` column (password vs app-cred) and a
  `User / Credential` column that displays the application-credential id
  for AC profiles; project cell shows `(pre-scoped)` for AC.

### Changed

- Shell-completion helpers moved from `commands/setup.py` to
  `core/shell_completion.py` and are shared by `setup` and `completion`.

## [1.1.0] — 2026-04-20

### Added

- Native `v3applicationcredential` auth in `OrcaClient` — id+secret or
  name+user reference, pre-scoped (no project/domain scope needed).
- `profile add` / `profile edit` / `setup` ask password vs application
  credential and round-trip the AC fields through `to-clouds` /
  `to-openrc` and `from-clouds` / `import-openrc`.
- Token cache key derived from credential identity (not user/project)
  when the auth type is application credential.
- `OS_AUTH_TYPE`, `OS_APPLICATION_CREDENTIAL_*` and `ORCA_*` equivalents
  wired through the config priority resolution.
- `orca application-credential create --save-profile NAME` persists the
  freshly minted AC directly as an orca profile.
- `orca hypervisor usage`: per-host CPU / RAM / disk fill rate with
  color-threshold bars, `--top`, `--threshold`, sort options.

### Fixed

- `application-credential` commands resolved the current user id from the
  token correctly (the token wrapper was being read twice, always falling
  back to the literal string `"me"`).

## [1.0.3] — 2026-04-19

### Added

- `orca rating` group — full CloudKitty coverage. Validated live against
  Infomaniak (dc3-a, non-admin).
  - End-user: `info`, `metric-list` / `metric-show`, `summary`,
    `dataframes` (v2 with v1 fallback), `quote`.
  - Admin: `module-list` / `module-show` / `module-enable` /
    `module-disable` / `module-set-priority` (hashmap, pyscripts, noop).
    Uses fetch-merge-PUT because CloudKitty `PUT` requires the full
    representation.
  - Admin (hashmap): `service-*`, `field-*`, `mapping-*` (flat/rate,
    field- or service-level), `threshold-*` (tiered pricing), `group-*`.

### Fixed

- `rating metric-show` path is `/v1/info/metrics/{id}` (plural);
  CloudKitty returns 405 on the singular form.
- `validate_id` passes `None` through so the callback is safe on optional
  Click parameters (needed by hashmap `--field-id`, `--service-id`,
  `--group-id` filters).

## [1.0.2] — 2026-04-19

### Fixed

- `alarm set`: Aodh requires the full alarm representation on `PUT`, not
  a partial. Fetch current, merge user updates, strip read-only fields
  (`alarm_id`, `project_id`, `user_id`, `timestamp`, `state_timestamp`,
  `state_reason*`), then `PUT`. Previously returned 400 on any update
  that didn't include `name` + `type` + `rule`.
- `validate_id` accepts 32-char bare-hex IDs alongside hyphenated UUIDs.
  Keystone projects/users/groups on many clouds (Infomaniak included) are
  exposed as hex-without-hyphens, which made
  `alarm quota-set <project_id>` and similar commands unusable.
- `__version__` reads from the installed package metadata via
  `importlib.metadata.version` instead of a hardcoded string that had
  drifted from `pyproject.toml`.

## [1.0.1] — 2026-04-19

### Fixed (P1 — production blockers)

- `server ssh` drops the permissive `orca-*` glob fallback, recognises
  `.pem` / `.key` variants, and reuses `_find_ssh_key` in the port-forward
  subcommand.
- `backup`: clarified that this group is Freezer (DR); Cinder volume
  backups live under `orca volume backup-*`.

### Fixed (P2 — UX)

- Distinguish 401 (`AuthenticationError`, triggers re-auth) from 403
  (`PermissionDeniedError` — valid token, insufficient role) across all
  HTTP helpers in `core/`, `image`, `container`, `object_store`.
- Sniff HTML error pages (`text/html` or `<!doctype` / `<html` prefix)
  and surface a clear "endpoint advertised in the catalogue but not
  exposed on this cloud" message.
- `event list` drops columns whose values are all empty; long UUID
  columns use `overflow=fold` instead of `no_wrap` to avoid zero-width
  cells in Rich tables.
- `server ssh` detects the distro of boot-from-volume servers via the
  attached volume's `volume_image_metadata.os_distro` (fixes Debian 12
  BFV `→ root`).

### Fixed (P3 — polish)

- `server shelve` / `unshelve`: new `--wait` flag (waits for
  `SHELVED_OFFLOADED` / `ACTIVE`).
- `flavor list`: `--limit` is now optional; auto-paginates via Nova
  marker otherwise.
- `audit`: ICMPv6 open to `0.0.0.0/0` downgraded CRITICAL → MEDIUM
  (RFC 4861 Neighbor Discovery / MLD is the expected baseline).
- `recordset list`: split SOA single-record on whitespace; render NS /
  MX / TXT multi-values one-per-line; ID column uses `overflow=fold`.

## [1.0.0] — 2026-04-16

Initial public release on PyPI as `orca-openstackclient`.

Services covered: Nova (compute, flavors, keypairs, server groups,
hypervisors), Neutron (networks, subnets, ports, routers, floating IPs,
security groups, QoS, trunks), Cinder (volumes, snapshots, backups),
Glance (images), Keystone (identity: domains, projects, users, groups,
roles, trusts, tokens, application credentials, federation, policies),
Octavia (load balancers, listeners, pools, members, health monitors),
Barbican (secrets, containers), Magnum (cluster templates, clusters),
Gnocchi (metrics, measures, resources, aggregations), Placement (resource
providers, inventories, allocations), Heat (stacks, events), Freezer
(backups), Designate (zones, recordsets), Aodh (alarms).

Orca-exclusive commands: `overview`, `watch`, `doctor`, `audit`,
`cleanup`, `export`, `find`, `ip-whois`.

Multi-profile config (`~/.orca/config.yaml`), `clouds.yaml` interop,
`OS_*` env var support, Keystone v3 password auth, Rich-powered output
(table / json / value), Bash + Zsh + Fish completion.

[1.3.0]: https://github.com/stackopshq/orca-cli/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/stackopshq/orca-cli/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/stackopshq/orca-cli/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/stackopshq/orca-cli/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/stackopshq/orca-cli/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/stackopshq/orca-cli/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/stackopshq/orca-cli/releases/tag/v1.0.0
