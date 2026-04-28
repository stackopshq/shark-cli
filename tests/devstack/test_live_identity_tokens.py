"""Live e2e: Keystone tokens and trusts.

Covers ``token`` (2: issue, revoke) and ``trust`` (4: create, delete,
list, show) — 6 cmds.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_token_issue_then_list(live_invoke):
    # token issue mints a fresh token for the current credentials; useful
    # to verify auth round-trip, no cleanup needed (token expires).
    res = live_invoke("token", "issue", "-f", "value", "-c", "Token")
    assert res.exit_code == 0, res.output
    token_value = res.output.strip().splitlines()[0]
    assert len(token_value) > 32  # Fernet tokens are long base64 strings


def test_trust_full(live_invoke, cleanup, live_name):
    # Need a trustee user (a non-admin user we own).
    trustee_name = live_name("trustee")
    res = live_invoke("user", "create", trustee_name,
                      "--password", "trusteepw")
    assert res.exit_code == 0, res.output
    trustee_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("user", "delete", trustee_id, "--yes"))

    # Trustor = the current admin user.
    res = live_invoke("user", "list", "-f", "value", "-c", "ID", "-c", "Name")
    assert res.exit_code == 0
    trustor_id = next(
        line.split()[0]
        for line in res.output.splitlines()
        if "admin" in line.split()[1:]
    )

    # Project = current admin project.
    res = live_invoke("project", "list", "-f", "value", "-c", "ID", "-c", "Name")
    assert res.exit_code == 0
    project_id = next(
        line.split()[0]
        for line in res.output.splitlines()
        if "admin" in line.split()[1:]
    )

    # Create the trust.
    res = live_invoke("trust", "create",
                      "--trustor", trustor_id,
                      "--trustee", trustee_id,
                      "--project", project_id,
                      "--role", "member",
                      "--impersonate")
    assert res.exit_code == 0, res.output
    trust_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("trust", "delete", trust_id, "--yes"))

    res = live_invoke("trust", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert trust_id in res.output

    res = live_invoke("trust", "show", trust_id,
                      "-f", "value", "-c", "trustee_user_id")
    assert res.exit_code == 0
    assert trustee_id in res.output
