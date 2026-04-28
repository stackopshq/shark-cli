"""Live e2e: complete coverage of Keystone core identity commands.

Exercises every sub-command of ``domain``, ``project``, ``user``,
``group``, and ``role`` (36 commands total) in a single coherent
scenario, with LIFO cleanup. Catches both per-command bugs and
inter-command bugs (e.g. group add-user expects a user that came
from a different create call).
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_identity_core_full(live_invoke, cleanup, live_name):
    # ── DOMAIN ─────────────────────────────────────────────────────────
    domain_name = live_name("dom")
    res = live_invoke("domain", "create", domain_name,
                      "--description", "live test domain")
    assert res.exit_code == 0, res.output
    domain_id = extract_uuid(res.output)

    def _cleanup_domain() -> None:
        live_invoke("domain", "set", domain_id, "--disable")
        live_invoke("domain", "delete", domain_id, "--yes")
    cleanup(_cleanup_domain)

    res = live_invoke("domain", "set", domain_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("domain", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert domain_id in res.output

    res = live_invoke("domain", "show", domain_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert domain_name in res.output

    # ── PROJECT ────────────────────────────────────────────────────────
    project_name = live_name("proj")
    res = live_invoke("project", "create", project_name,
                      "--domain", domain_id,
                      "--description", "live test project")
    assert res.exit_code == 0, res.output
    project_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", project_id, "--yes"))

    res = live_invoke("project", "set", project_id, "--description", "p-updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("project", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert project_id in res.output

    res = live_invoke("project", "show", project_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert project_name in res.output

    # project cleanup --dry-run on an empty project — no resources to delete,
    # but exercises the command path through every Nova/Cinder/Neutron list.
    res = live_invoke("project", "cleanup",
                      "--project", project_id, "--dry-run", "--yes")
    assert res.exit_code == 0, res.output

    # ── USER ───────────────────────────────────────────────────────────
    user_name = live_name("user")
    res = live_invoke("user", "create", user_name,
                      "--domain", domain_id,
                      "--password", "initialpw",
                      "--description", "live test user",
                      "--email", "live@example.com")
    assert res.exit_code == 0, res.output
    user_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("user", "delete", user_id, "--yes"))

    res = live_invoke("user", "set", user_id, "--description", "u-updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("user", "set-password", user_id, "--password", "newpw")
    assert res.exit_code == 0, res.output

    res = live_invoke("user", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert user_id in res.output

    res = live_invoke("user", "show", user_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert user_name in res.output

    # ── GROUP ──────────────────────────────────────────────────────────
    group_name = live_name("grp")
    res = live_invoke("group", "create", group_name,
                      "--domain", domain_id,
                      "--description", "live test group")
    assert res.exit_code == 0, res.output
    group_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("group", "delete", group_id, "--yes"))

    res = live_invoke("group", "set", group_id, "--description", "g-updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("group", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert group_id in res.output

    res = live_invoke("group", "show", group_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert group_name in res.output

    # group membership lifecycle
    res = live_invoke("group", "add-user", group_id, user_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("group", "member-list", group_id, "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert user_id in res.output

    res = live_invoke("group", "remove-user", group_id, user_id)
    assert res.exit_code == 0, res.output

    # ── ROLE ───────────────────────────────────────────────────────────
    role_name = live_name("role")
    res = live_invoke("role", "create", role_name,
                      "--description", "live test role")
    assert res.exit_code == 0, res.output
    role_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("role", "delete", role_id, "--yes"))

    role_renamed = role_name + "-r"
    res = live_invoke("role", "set", role_id, "--name", role_renamed)
    assert res.exit_code == 0, res.output

    res = live_invoke("role", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert role_id in res.output

    res = live_invoke("role", "show", role_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert role_renamed in res.output

    # ── ROLE ASSIGNMENT ────────────────────────────────────────────────
    res = live_invoke("role", "add", role_id,
                      "--user", user_id, "--project", project_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("role", "remove", role_id,
                                "--user", user_id, "--project", project_id))

    res = live_invoke("role", "assignment-list",
                      "--user", user_id, "--project", project_id,
                      "-f", "value", "-c", "Role ID")
    assert res.exit_code == 0, res.output
    assert role_id in res.output

    # ── ROLE INFERENCE ─────────────────────────────────────────────────
    role2_name = live_name("role2")
    res = live_invoke("role", "create", role2_name)
    assert res.exit_code == 0, res.output
    role2_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("role", "delete", role2_id, "--yes"))

    res = live_invoke("role", "implied-create", role_id, role2_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("role", "implied-delete",
                                role_id, role2_id, "--yes"))

    res = live_invoke("role", "implied-list", "-f", "value")
    assert res.exit_code == 0, res.output
    assert role_id in res.output
    assert role2_id in res.output
