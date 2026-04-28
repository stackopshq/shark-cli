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
- `volume upload-to-image` — mirrors the Cinder action name
  `os-volume_upload_image`. Compound verb; nesting it as
  `volume image upload` would imply `image` is a sub-resource of
  `volume`, when Glance is in fact the *target* of the action.

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
  commands kept as deprecated façades. Whitelist for `volume` was
  initially empty; `upload-to-image` was later added as a permanent
  exception (compound verb, see above).
- 2026-04-20 — `network`: 38 commands moved into 7 sub-groups
  (`agent`, `auto-allocated-topology` — compound noun, `port`,
  `rbac`, `segment`, `subnet`, `router`) and 4 sub-sub-groups under
  `router` (`add`, `remove`, `set`, `unset`). The ratchet test now
  excludes sub-groups whose name is itself a compound noun, in
  line with the ADR's "compound nouns keep their hyphen" rule.
  Whitelist for `network` is empty — no permanent exceptions.
- 2026-04-28 — **lot 1** (modules with ≤ 4 hyphenated leaves):
  `aggregate`, `alarm`, `auth`, `endpoint-group`, `flavor`, `group`,
  `role`, `secret` (acl-*), `security-group`, `trunk`, `user`
  (`set-password`). 26 commands moved to 12 new sub-groups
  (`aggregate host`, `aggregate image`, `alarm state`, `alarm quota`,
  `auth token`, `endpoint-group project`, `flavor access`, `group user`,
  `group member`, `role assignment`, `role implied`, `secret acl`,
  `security-group rule`, `trunk subport`, `user password`). All old
  hyphenated names live on as deprecated aliases via
  `add_command_with_alias`. Whitelists for these modules cleared.
- 2026-04-28 — **stack/zone/image admin** (gap-closure with OSC):
  `stack` gained `snapshot/{create,delete,list,show,restore}`,
  `adopt`, `environment show`, `failures list`, `file list`, and
  three `resource` actions (`signal`, `metadata`, `mark-unhealthy`).
  `zone` gained `abandon`, `axfr`, `share/*`, `blacklist/*`. `image`
  gained the full `metadef/*` catalogue (namespaces, objects,
  properties, resource-type associations). All new commands follow
  ADR-0008 from day one (no aliases needed).
- 2026-04-28 — **lots 2 + 3** (`zone`, `stack`): zone keeps
  `reverse-lookup` as a permanent exception (compound verb, no OSC
  equivalent); `tld-*` and `transfer-*` migrate to `tld {list,create,
  show,delete}`, `transfer request {list,create,show,delete}`,
  `transfer accept {list,create,show}`. `stack` migrates every
  former hyphenated leaf into a sub-group (`event`, `output`,
  `resource`, `template`, `resource-type`); old names live as
  deprecated aliases.
- 2026-04-28 — **lots 4 + 5** (`object`, `qos`): object's
  `account-*` and `container-*` move under `object account` and
  `object container`. qos splits into `qos policy` and `qos rule`
  (every former hyphenated leaf migrated).
- 2026-04-28 — **lot 6** (`rating`, `metric`): rating splits into
  `rating metric {list,create,delete}` and `rating module {list,
  enable,disable,set-priority}` (set-priority is a compound verb
  whitelisted on the module sub-group). metric migrates `archive-
  policy-*`, `resource-type-*`, `resource-{list,show}`, and
  `measures-*` under sub-groups (`archive-policy`, `resource-type`,
  `resource`, `measures`); `archive-policy` and `resource-type`
  keep their hyphen as compound-noun sub-group names.
- 2026-04-28 — **lot 7** (`image`): `cache-*`, `member-*`, `tag-*`,
  `task-*`, `stores-*` move under `image cache`, `image member`,
  `image tag`, `image task`, `image stores`. `share-and-accept`
  remains a permanent exception (orca-specific compound verb that
  bundles `member-create + member-set --status accepted`).
- 2026-04-28 — **lot 8** (`loadbalancer`): 35 former hyphenated
  leaves migrate to nine sub-groups (`amphora`, `healthmonitor`,
  `l7policy`, `l7rule`, `listener`, `member`, `pool`, `stats`,
  `status`). `l7policy` and `l7rule` keep their hyphen as
  compound-noun sub-group names.
- 2026-04-28 — **lot 9** (`placement`): 29 former hyphenated leaves
  migrate to five sub-groups (`resource-provider`, `resource-class`,
  `trait`, `allocation`, `usage`). Sub-leaves of resource-provider
  (`inventory-list/set/show/delete-all`, `trait-list/set/delete`,
  `aggregate-list/set/delete`) and `allocation candidate-list` keep
  their hyphen as compound nouns/verbs that read as one phrase.
- 2026-04-28 — **lot 10** (`backup`, `cluster`): backup's 21
  hyphenated leaves migrate to four sub-groups (`action`, `client`,
  `job`, `session`); `session add-job` and `session remove-job`
  remain hyphenated as compound verbs nested under the `session`
  sub-group. cluster's 9 hyphenated leaves migrate to two
  sub-groups (`nodegroup`, `template`). All 30 old names live as
  deprecated aliases via `add_command_with_alias`. Whitelists for
  `backup` and `cluster` cleared.
- 2026-04-28 — **lot 11** (`profile`): the last 6 hyphenated leaves
  migrate to four sub-groups (`color`, `region`, `import`,
  `export`) — `set-color` → `color set`, `set-region` →
  `region set`, `to-openrc`/`to-clouds` → `export openrc`/
  `export clouds`, `from-openrc`/`from-clouds` →
  `import openrc`/`import clouds`. The single-word `regions` leaf
  also moves under the new `region` sub-group as `region list` for
  consistency. All 7 legacy names live on as deprecated aliases.
  Whitelist for `profile` cleared — **migration complete**:
  every command in the live tree now follows ADR-0008.
