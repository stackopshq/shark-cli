# ADR-0008: Command naming follows the openstackclient convention

**Status**: Accepted
**Date**: 2026-04-20

## Context

orca's command tree grew organically. A scan of the 649 subcommands at
2026-04-20 found that **332 of them (51 %)** use a `verb-noun` or
`subnoun-verb` form glued by hyphens, instead of the
`noun [subnoun] verb` shape used by the canonical `openstack` CLI:

| Current orca | openstack equivalent |
|---|---|
| `orca server list-volumes` | `openstack server volume list` |
| `orca server attach-volume` | `openstack server add volume` |
| `orca server migration-list` | `openstack server migration list` |
| `orca volume snapshot-create` | `openstack volume snapshot create` |
| `orca network router-add-interface` | `openstack network router add interface` |
| `orca loadbalancer listener-create` | `openstack loadbalancer listener create` |

The friction this causes:

- A user who already knows `openstack` has to relearn each command —
  exactly the audience orca wants to attract.
- Discoverability is poor: tab-completing `orca server <TAB>` shows a
  flat list of 60 entries instead of a few logical sub-groups.
- Modules ended up incoherent with each other (e.g. `server attach-volume`
  vs. `volume attachment-create` — both legitimate today, both wrong
  tomorrow).

The full inventory by module (top 10):

| Module | Subcommands | Hyphenated | % |
|---|---|---|---|
| `volume` | 71 | 59 | 83 |
| `placement` | 29 | 29 | 100 |
| `network` | 45 | 38 | 84 |
| `loadbalancer` | 40 | 35 | 88 |
| `server` | 60 | 28 | 47 |
| `backup` | 24 | 21 | 88 |
| `image` | 28 | 15 | 54 |
| `secret` | 16 | 12 | 75 |
| `metric` | 17 | 11 | 65 |
| `stack` | 22 | 10 | 45 |

## Decision

### Convention

1. **Top-level group** = the resource as a noun. Compound nouns keep
   their hyphen because they read as one word (`floating-ip`,
   `security-group`, `availability-zone`). This matches both
   `openstack` and existing orca usage.

2. **Subcommand** = the verb (`list`, `show`, `create`, `delete`,
   `set`, `unset`, `add`, `remove`).

3. **Sub-resources nest as their own group**, never glue a sub-resource
   name to a verb:
   - ✅ `orca server migration list`
   - ❌ `orca server migration-list`

4. **Multi-word objects after a verb keep the hyphen** (the noun is
   compound, not a verb-noun glue):
   - ✅ `orca server add fixed-ip`
   - ❌ `orca server add-fixed-ip`

5. **Existing hyphenated commands get aliases**: when a module is
   refactored, the new (compliant) command becomes primary and the old
   name is registered as an alias on the same callback, with
   `[deprecated, use 'X Y' instead]` appended to its short help.
   Aliases are removed in **v2.0**.

### Migration policy

- **No flag day.** Migration happens module-by-module, opportunistically
  when a module is refactored anyway (e.g. alongside an ADR-0007
  service migration).
- **Ratchet:** a test scans the live command tree for hyphenated
  subcommands and compares against a whitelist of the 332 known
  legacy names. Any new hyphenated subcommand not in the whitelist
  fails the test — the debt can only shrink.

### Order (driven by usage and pain, not module size)

1. `server` (already in flight via ADR-0007)
2. `volume`, `network`, `image` — most-used, biggest impact
3. `loadbalancer`, `placement`, `backup` — heavy noise, low daily usage
4. The rest, opportunistically

## Consequences

- **Positive**: an `openstack` user can guess most orca commands without
  reading the docs.
- **Positive**: `--help` output for each group becomes shorter and more
  organised once subnouns nest properly.
- **Positive**: the ratchet test makes it impossible to add new debt by
  accident.
- **Negative / trade-off**: each refactor doubles the surface for one
  release cycle (primary + alias). Worth it for non-breaking migration.
- **Negative / trade-off**: the migration is multi-week and won't be
  finished in one session. Tracked here as it progresses.

## Permanent exceptions

Some hyphenated names are kept on purpose because the convention
either does not fit them or would force gymnastics that hurt
ergonomics more than they help. Each one is documented inline in
`tests/test_naming_convention.py` so the choice survives a future
re-read.

- `server confirm-resize`, `server revert-resize` — `resize` is both
  an action (`server resize <id> --flavor ...`) and would need to be
  a sub-group to host `confirm`/`revert`. Click can do this with
  `invoke_without_command=True` but the resulting `--help` mixes
  arguments and sub-commands awkwardly. The hyphenated form is clear
  enough; not worth the acrobatics.
- `server port-forward` — orca-exclusive (no openstack equivalent).
  Compound verb that reads naturally; nesting it under a sub-group
  (`server tunnel forward`) would gain nothing since there are no
  sibling commands.

Adding to this list requires a deliberate choice and an inline
comment in the test whitelist explaining why.

## Migration tracking

Update this list when a module's hyphenated commands are migrated.

- 2026-04-20 — `server`: 23 commands moved to nested sub-groups
  (`add`, `remove`, `console`, `dump`, `image`, `interface`,
  `metadata`, `migration`, `tag`, `volume`); `attach-interface` and
  `live-migrate` reduced to deprecated façades that warn and
  forward. Three permanent exceptions remain (see above).
- 2026-04-20 — `volume`: 54 commands moved into 9 sub-groups and 3
  sub-sub-groups (`attachment`, `backup`, `group`, `group snapshot`,
  `group type`, `message`, `qos`, `service`, `snapshot`, `transfer`,
  `type`, `type access`). `revert-to-snapshot` becomes
  `volume snapshot revert`. `set-bootable` / `set-readonly` fold
  into `volume set --bootable` / `--read-only` with the two old
  commands kept as deprecated façades. Whitelist for `volume` is
  empty — no permanent exceptions.
- 2026-04-20 — `network`: 38 commands moved into 7 sub-groups
  (`agent`, `auto-allocated-topology` — compound noun, `port`,
  `rbac`, `segment`, `subnet`, `router`) and 4 sub-sub-groups under
  `router` (`add`, `remove`, `set`, `unset`). The ratchet test now
  excludes sub-groups whose name is itself a compound noun, in
  line with the ADR's "compound nouns keep their hyphen" rule.
  Whitelist for `network` is empty — no permanent exceptions.
