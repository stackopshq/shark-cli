"""Ratchet test for ADR-0008 — command naming convention.

Every hyphenated subcommand currently shipping is listed in the
``LEGACY_HYPHENATED_SUBCOMMANDS`` whitelist. The test fails if:

- a *new* hyphenated subcommand appears anywhere in the live command
  tree without being added to the whitelist (regression — the new
  command should follow ``noun [subnoun] verb`` instead).
- a name in the whitelist no longer exists (it was removed or
  renamed — clean it up so the whitelist keeps shrinking).

To migrate a legacy command:

1. Refactor the module to expose the new ``noun subnoun verb`` form.
2. Keep the old hyphenated name as an alias on the same callback.
3. Remove the old name from the whitelist below.

This way the debt can only shrink — see ADR-0008.
"""

from __future__ import annotations

import click

from orca_cli.main import cli

LEGACY_HYPHENATED_SUBCOMMANDS: dict[str, set[str]] = {
    # Modules migrated 2026-04 (lot 1) — old names live on as deprecated
    # aliases, excluded from the live tree by the runtime: aggregate,
    # alarm, auth, endpoint-group, flavor, group, role, secret (acl-*),
    # security-group, trunk, user (set-password).
    "backup": {
        "action-create", "action-delete", "action-list", "action-show",
        "client-delete", "client-list", "client-register", "client-show",
        "job-create", "job-delete", "job-list", "job-show", "job-start",
        "job-stop", "session-add-job", "session-create", "session-delete",
        "session-list", "session-remove-job", "session-show", "session-start",
    },
    "cluster": {
        "nodegroup-create", "nodegroup-delete", "nodegroup-list",
        "nodegroup-show", "nodegroup-update",
        "template-create", "template-delete", "template-list", "template-show",
    },
    "floating-ip": {"bulk-release"},
    "image": {
        "cache-clear", "cache-delete", "cache-list", "cache-queue",
        "member-create", "member-delete", "member-list", "member-set",
        "member-show", "share-and-accept", "stores-info",
        "tag-add", "tag-delete", "task-list", "task-show",
    },
    "loadbalancer": {
        "amphora-failover", "amphora-list", "amphora-show",
        "healthmonitor-create", "healthmonitor-delete", "healthmonitor-list",
        "healthmonitor-set", "healthmonitor-show",
        "l7policy-create", "l7policy-delete", "l7policy-list",
        "l7policy-set", "l7policy-show",
        "l7rule-create", "l7rule-delete", "l7rule-list",
        "l7rule-set", "l7rule-show",
        "listener-create", "listener-delete", "listener-list",
        "listener-set", "listener-show",
        "member-add", "member-list", "member-remove", "member-set", "member-show",
        "pool-create", "pool-delete", "pool-list", "pool-set", "pool-show",
        "stats-show", "status-show",
    },
    "metric": {
        "archive-policy-create", "archive-policy-delete",
        "archive-policy-list", "archive-policy-show",
        "measures-add",
        "resource-list", "resource-show",
        "resource-type-create", "resource-type-delete",
        "resource-type-list", "resource-type-show",
    },
    # "network" entry removed — every former hyphenated subcommand is now
    # nested under a sub-group (agent, port, rbac, segment, subnet,
    # auto-allocated-topology, router) or sub-sub-group (router add/remove
    # for interface/route, router set/unset for gateway).
    "object": {
        "account-set", "account-unset",
        "container-create", "container-delete", "container-list",
        "container-save", "container-set", "container-show",
    },
    "placement": {
        "allocation-candidate-list", "allocation-delete", "allocation-set",
        "allocation-show",
        "resource-class-create", "resource-class-delete",
        "resource-class-list", "resource-class-show",
        "resource-provider-aggregate-delete",
        "resource-provider-aggregate-list",
        "resource-provider-aggregate-set",
        "resource-provider-create", "resource-provider-delete",
        "resource-provider-inventory-delete",
        "resource-provider-inventory-delete-all",
        "resource-provider-inventory-list",
        "resource-provider-inventory-set",
        "resource-provider-inventory-show",
        "resource-provider-list", "resource-provider-set",
        "resource-provider-show",
        "resource-provider-trait-delete", "resource-provider-trait-list",
        "resource-provider-trait-set", "resource-provider-usage",
        "trait-create", "trait-delete", "trait-list", "usage-list",
    },
    "profile": {
        "from-clouds", "from-openrc",
        "set-color", "set-region",
        "to-clouds", "to-openrc",
    },
    "qos": {
        "policy-create", "policy-delete", "policy-list",
        "policy-set", "policy-show",
        "rule-create", "rule-delete", "rule-list",
    },
    "rating": {
        "metric-list", "metric-show",
        "module-disable", "module-enable", "module-list",
        "module-set-priority", "module-show",
    },
    "secret": {
        "container-create", "container-delete", "container-list",
        "container-show", "get-payload",
        "order-create", "order-delete", "order-list", "order-show",
    },
    "server": {
        # Decided exceptions (arbitrated, kept on purpose):
        # - confirm-resize / revert-resize: `resize` is both an action
        #   (`server resize <id> --flavor ...`) and would need to be a
        #   sub-group; statu quo, not worth the Click acrobatics.
        # - port-forward: orca-exclusive (no openstack equivalent),
        #   compound verb, kept as-is.
        # Note: attach-interface and live-migrate are now `deprecated=True`
        # façades and excluded from this whitelist automatically by the
        # test runtime.
        "confirm-resize",
        "port-forward",
        "revert-resize",
    },
    # stack — migrated 2026-04-28: every leaf moved into a sub-group
    # (event/output/resource/resource-type/template); old hyphenated
    # names live as deprecated aliases.
    "volume": {
        # Deliberate exception (compound verb, no openstack equivalent):
        # ``upload-to-image`` mirrors the Cinder action name
        # ``os-volume_upload_image`` and reads as a single verb phrase.
        # Nesting it under a sub-group (e.g. ``volume image upload``)
        # would suggest ``image`` is a sub-resource of ``volume``, which
        # it isn't — Glance is just the target system. Same rationale
        # as ``server port-forward``.
        "upload-to-image",
    },
    "zone": {
        # ``reverse-lookup`` is a compound verb (orca-specific UX, no
        # OSC equivalent) — kept on purpose. Other tld-* and
        # transfer-* names are deprecated aliases excluded by the
        # runtime.
        "reverse-lookup",
    },
}


def _live_hyphenated_subcommands() -> dict[str, set[str]]:
    """Walk the cli tree and return {top-group: {hyphenated-leaf-names}}.

    Two classes of hyphenated names are excluded by design:

    - Deprecated aliases (``deprecated=True``, registered via
      ``add_command_with_alias``) — tracked separately as part of the
      alias-and-deprecate plan, not as fresh debt.
    - Sub-groups whose own name is a compound noun (e.g.
      ``auto-allocated-topology``) — ADR-0008 explicitly allows
      compound nouns to keep their hyphen because they read as one
      word. The convention only forbids ``verb-noun`` glue on *leaf*
      commands.
    """
    out: dict[str, set[str]] = {}
    for top_name in cli.list_commands(None):
        top = cli.get_command(None, top_name)
        if not isinstance(top, click.Group):
            continue
        hy = {
            s for s, cmd in top.commands.items()
            if "-" in s
            and not getattr(cmd, "deprecated", False)
            and not isinstance(cmd, click.Group)
        }
        if hy:
            out[top_name] = hy
    return out


def test_no_new_hyphenated_subcommand_outside_whitelist():
    """A new hyphenated subcommand must violate this test (see ADR-0008)."""
    live = _live_hyphenated_subcommands()
    new: dict[str, set[str]] = {}
    for top, names in live.items():
        legacy = LEGACY_HYPHENATED_SUBCOMMANDS.get(top, set())
        extras = names - legacy
        if extras:
            new[top] = extras

    assert not new, (
        "New hyphenated subcommand(s) detected — name them with the "
        "openstackclient convention (noun [subnoun] verb) per ADR-0008, "
        "or add to the whitelist if it is a deliberate exception:\n"
        + "\n".join(f"  {top}: {sorted(extras)}" for top, extras in new.items())
    )


def test_whitelist_does_not_carry_dead_entries():
    """Whitelist names that no longer exist in the cli must be removed."""
    live = _live_hyphenated_subcommands()
    stale: dict[str, set[str]] = {}
    for top, legacy in LEGACY_HYPHENATED_SUBCOMMANDS.items():
        live_names = live.get(top, set())
        gone = legacy - live_names
        if gone:
            stale[top] = gone

    assert not stale, (
        "Whitelist references commands that no longer exist — drop them "
        "from tests/test_naming_convention.py:\n"
        + "\n".join(f"  {top}: {sorted(gone)}" for top, gone in stale.items())
    )
