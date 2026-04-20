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
    "aggregate": {"add-host", "cache-image", "remove-host"},
    "alarm": {"quota-set", "state-get", "state-set"},
    "auth": {"token-debug", "token-revoke"},
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
    "endpoint-group": {"add-project", "remove-project"},
    "flavor": {"access-add", "access-list", "access-remove"},
    "floating-ip": {"bulk-release"},
    "group": {"add-user", "member-list", "remove-user"},
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
    "network": {
        "agent-delete", "agent-list", "agent-set", "agent-show",
        "auto-allocated-topology-delete", "auto-allocated-topology-show",
        "port-create", "port-delete", "port-list", "port-show",
        "port-unset", "port-update",
        "rbac-create", "rbac-delete", "rbac-list", "rbac-show", "rbac-update",
        "router-add-interface", "router-add-route",
        "router-create", "router-delete", "router-list",
        "router-remove-interface", "router-remove-route",
        "router-set-gateway", "router-show", "router-unset-gateway",
        "router-update",
        "segment-create", "segment-delete", "segment-list",
        "segment-set", "segment-show",
        "subnet-create", "subnet-delete", "subnet-list",
        "subnet-show", "subnet-update",
    },
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
    "role": {
        "assignment-list",
        "implied-create", "implied-delete", "implied-list",
    },
    "secret": {
        "acl-delete", "acl-get", "acl-set",
        "container-create", "container-delete", "container-list",
        "container-show", "get-payload",
        "order-create", "order-delete", "order-list", "order-show",
    },
    "security-group": {"rule-add", "rule-delete"},
    "server": {
        # Cases pending arbitration — see ADR-0008 migration tracking:
        # - confirm-resize / revert-resize would clash with `resize` as
        #   both an action (`server resize <id> --flavor ...`) and a
        #   sub-group; needs a Click pattern decision.
        # - live-migrate is a compound verb without a clean sub-group
        #   shape in openstackclient either.
        # - port-forward is orca-exclusive (no openstack equivalent).
        # Note: attach-interface is now `deprecated=True` (façade with
        # smart dispatch warning) and excluded from this whitelist by
        # the test runtime.
        "confirm-resize",
        "live-migrate",
        "port-forward",
        "revert-resize",
    },
    "stack": {
        "event-list", "event-show", "output-list", "output-show",
        "resource-list", "resource-show",
        "resource-type-list", "resource-type-show",
        "template-show", "template-validate",
    },
    "trunk": {"add-subport", "remove-subport", "subport-list"},
    "user": {"set-password"},
    "volume": {
        "attachment-complete", "attachment-create", "attachment-delete",
        "attachment-list", "attachment-set", "attachment-show",
        "backup-create", "backup-delete", "backup-list",
        "backup-restore", "backup-show",
        "group-create", "group-delete", "group-list", "group-show",
        "group-snapshot-create", "group-snapshot-delete",
        "group-snapshot-list", "group-snapshot-show",
        "group-type-create", "group-type-delete", "group-type-list",
        "group-type-set", "group-type-show", "group-type-unset",
        "group-update",
        "message-delete", "message-list", "message-show",
        "qos-associate", "qos-create", "qos-delete", "qos-disassociate",
        "qos-list", "qos-set", "qos-show",
        "revert-to-snapshot",
        "service-list", "service-set",
        "set-bootable", "set-readonly",
        "snapshot-create", "snapshot-delete", "snapshot-list",
        "snapshot-set", "snapshot-show",
        "transfer-accept", "transfer-create", "transfer-delete",
        "transfer-list", "transfer-show",
        "type-access-add", "type-access-list", "type-access-remove",
        "type-create", "type-delete", "type-list", "type-set", "type-show",
    },
    "zone": {
        "reverse-lookup",
        "tld-create", "tld-delete", "tld-list",
        "transfer-accept",
        "transfer-request-create", "transfer-request-delete",
        "transfer-request-list", "transfer-request-show",
    },
}


def _live_hyphenated_subcommands() -> dict[str, set[str]]:
    """Walk the cli tree and return {top-group: {hyphenated-sub-names}}.

    Deprecated aliases (those marked ``deprecated=True``, registered via
    ``add_command_with_alias``) are excluded — they are tracked
    elsewhere as part of the alias-and-deprecate plan, not as fresh
    debt.
    """
    out: dict[str, set[str]] = {}
    for top_name in cli.list_commands(None):
        top = cli.get_command(None, top_name)
        if not isinstance(top, click.Group):
            continue
        hy = {
            s for s, cmd in top.commands.items()
            if "-" in s and not getattr(cmd, "deprecated", False)
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
