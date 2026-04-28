"""Live e2e: Keystone policies and unified limits.

Covers ``policy`` (5), ``limit`` (5), ``registered-limit`` (5) — 15 cmds.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_identity_governance_full(live_invoke, cleanup, live_name):
    # ── POLICY ────────────────────────────────────────────────────────
    blob = '{"identity:list_users": "rule:admin_required"}'
    res = live_invoke("policy", "create", blob,
                      "--type", "application/json")
    assert res.exit_code == 0, res.output
    policy_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("policy", "delete", policy_id, "--yes"))

    new_blob = '{"identity:list_users": "rule:admin_or_owner"}'
    res = live_invoke("policy", "set", policy_id, "--blob", new_blob)
    assert res.exit_code == 0, res.output

    res = live_invoke("policy", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert policy_id in res.output

    res = live_invoke("policy", "show", policy_id, "-f", "value", "-c", "type")
    assert res.exit_code == 0
    assert "json" in res.output

    # ── REGISTERED LIMIT (default per service+resource) ─────────────────
    # Need a service to attach the limit to. Create one.
    svc_name = live_name("svc")
    svc_type = "live-test-" + svc_name[-8:]
    res = live_invoke("service", "create",
                      "--name", svc_name, "--type", svc_type)
    assert res.exit_code == 0, res.output
    svc_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("service", "delete", svc_id, "--yes"))

    res = live_invoke("registered-limit", "create",
                      "--service-id", svc_id,
                      "--resource-name", "live_test_resource",
                      "--default-limit", "100",
                      "--description", "live test")
    assert res.exit_code == 0, res.output
    rl_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("registered-limit", "delete", rl_id, "--yes"))

    res = live_invoke("registered-limit", "set", rl_id, "--default-limit", "200")
    assert res.exit_code == 0, res.output

    res = live_invoke("registered-limit", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert rl_id in res.output

    res = live_invoke("registered-limit", "show", rl_id,
                      "-f", "value", "-c", "Default Limit")
    assert res.exit_code == 0
    assert "200" in res.output

    # ── PROJECT LIMIT (project-specific override of registered-limit) ──
    # Need a project + the registered-limit to be in place.
    proj_name = live_name("limproj")
    res = live_invoke("project", "create", proj_name)
    assert res.exit_code == 0, res.output
    proj_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", proj_id, "--yes"))

    res = live_invoke("limit", "create",
                      "--project-id", proj_id,
                      "--service-id", svc_id,
                      "--resource-name", "live_test_resource",
                      "--resource-limit", "50",
                      "--description", "live test override")
    assert res.exit_code == 0, res.output
    lim_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("limit", "delete", lim_id, "--yes"))

    res = live_invoke("limit", "set", lim_id, "--resource-limit", "75")
    assert res.exit_code == 0, res.output

    # `limit list` requires a system-scoped token to return entries; our
    # profile is project-scoped (admin/admin), so the list is empty by
    # design. We only assert the call goes through cleanly.
    res = live_invoke("limit", "list",
                      "--project-id", proj_id,
                      "-f", "value", "-c", "ID")
    assert res.exit_code == 0

    res = live_invoke("limit", "show", lim_id,
                      "-f", "value", "-c", "Resource Limit")
    assert res.exit_code == 0
    assert "75" in res.output
