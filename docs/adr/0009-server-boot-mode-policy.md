# ADR-0009: Server boot mode defaults to boot-from-image

**Status**: Accepted
**Date**: 2026-04-23

## Context

Until v2.0.1, `orca server create` and `orca server clone` built an
unconditional `block_device_mapping_v2` with
`source_type=image, destination_type=volume`, asking Nova to create a
Cinder volume from the image for every boot. The docstring even advertised
this as *"Create a new server (boot from volume)"*.

Forcing boot-from-volume (BFV) uniformly has real costs on any cloud where
the flavor can carry a local root disk:

- **Cinder quota is consumed per VM**, even for a 5-minute test instance.
  A cleanup run on 2026-04-23 with 30 ephemeral test VMs left 30 boot
  volumes attached; they cascaded as 404s during `project cleanup`.
- **Provisioning is slower**: Cinder must materialise the volume from the
  image before Nova schedules the VM (3–10 s typical, more on a busy
  backend).
- **The flavor's `disk` field becomes dead** — allocated but unused.
- **Horizon and the dashboard default** is boot-from-image with an
  opt-in checkbox for boot-from-volume; an `openstack`-trained user
  expects `orca server create --image X` to behave the same way.

The one case where BFV is actually required is flavors declared with
`disk == 0`. Nova refuses to schedule an ephemeral boot on such a
flavor because there is no root-disk allocation; Cinder is the only
backing available.

## Decision

**`orca server create` and `orca server clone` boot from image by
default.** The Nova body uses `imageRef` and no
`block_device_mapping_v2`; Nova sizes the root disk from the flavor.

The policy lives in a single helper `_resolve_boot_mode(client,
flavor_id, boot_from_image, boot_from_volume)` that both commands call.
Precedence:

1. `--boot-from-volume` explicit → BFV, regardless of flavor.
2. `--boot-from-image` explicit → ephemeral; errors with a clear
   message if `flavor.disk == 0`.
3. Neither flag → auto: ephemeral when `flavor.disk > 0`, BFV when
   `flavor.disk == 0`.

The two flags are mutually exclusive. When the flavor lookup itself
fails (transient Nova error, missing permissions), the explicit flag
is honoured; without one the helper falls back to BFV, which works on
every deployment.

`--disk-size` keeps its meaning on the BFV path (boot volume size in
GB) and is ignored on the ephemeral path (Nova sizes the root disk
from the flavor — `--disk-size` there would silently have no effect,
not surface an error).

## Consequences

- **Positive**: default behaviour matches Horizon, `openstack server
  create`, and user expectations. No silent Cinder quota drain per VM.
- **Positive**: faster server creation on flavors with `disk > 0`.
- **Positive**: `project cleanup` output shrinks — no more wave of
  cascaded boot-volume 404s after deleting test fleets.
- **Negative / trade-off**: **backwards-incompatible** for pipelines
  that relied on the root Cinder volume being auto-created. Migration
  is a single flag (`--boot-from-volume`); documented in the PRs that
  landed the change and in `--help` output.
- **Negative / trade-off**: the command now issues one extra `GET
  /flavors/<id>` on auto-detection. This is ~10 ms and cached by
  Nova — acceptable.
- **Neutral**: the interactive wizard (`-i`) does not prompt for boot
  mode; it follows the same auto-detection. A future change could
  surface the choice if users request it, but keeping the wizard
  mirror of the non-interactive defaults keeps the two paths aligned.

## Alternatives considered

1. **Keep BFV unconditional (status quo)**. Rejected: silently wastes
   Cinder quota and provisioning time on the majority case.
2. **Flip to ephemeral unconditionally**. Rejected: breaks any flavor
   with `disk=0` without recourse. Auto-detection is the minimum
   required to stay operable on every cloud.
3. **Expose the flag as `--ephemeral / --boot-from-volume`**.
   Rejected: mixes a storage-type term (`ephemeral`) with an action
   term (`boot-from-volume`). The Horizon and docs vocabulary is
   `boot from image` / `boot from volume`; the flag pair should
   mirror that.

## Implementation

- `orca_cli/commands/server.py` — `_resolve_boot_mode` + two flags on
  `server create` and `server clone`.
- `tests/test_server_create_boot_mode.py` — 8 tests.
- `tests/test_server_clone_boot_mode.py` — 6 tests.
- Initial landing: PR #3 (create), PR #4 (clone).
