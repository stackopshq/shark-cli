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

## Migration tracking

Update this list when a module's hyphenated commands are migrated.

- *(none yet — `server` migration started below ADR-0007 will be the
  first to apply this convention as part of its remaining work)*
