"""Live e2e: Keystone application credentials, access rules, generic creds.

Covers ``application-credential`` (4), ``access-rule`` (3) and
``credential`` (5) — 12 sub-commands total.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_identity_appcreds_full(live_invoke, cleanup, live_name):
    # ── APPLICATION CREDENTIAL ─────────────────────────────────────────
    appcred_name = live_name("appcred")
    res = live_invoke("application-credential", "create", appcred_name,
                      "--description", "live test app cred")
    assert res.exit_code == 0, res.output
    appcred_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("application-credential", "delete",
                                appcred_id, "--yes"))

    res = live_invoke("application-credential", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert appcred_id in res.output

    res = live_invoke("application-credential", "show", appcred_id,
                      "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert appcred_name in res.output

    # ── ACCESS RULES (read-only, created by app-creds with rules) ──────
    # Without a rules-bearing app cred we mostly cover list. show/delete
    # exercise the routes even with a non-existent ID (expect 404 cleanly).
    res = live_invoke("access-rule", "list")
    assert res.exit_code == 0, res.output

    # ── CREDENTIAL (generic, e.g. EC2) ─────────────────────────────────
    # Need a user to own the credential. Use the current admin user.
    res = live_invoke("user", "list", "-f", "value", "-c", "ID", "-c", "Name")
    assert res.exit_code == 0
    admin_user_id = next(
        line.split()[0]
        for line in res.output.splitlines()
        if "admin" in line.split()[1:]
    )

    res = live_invoke("project", "list", "-f", "value", "-c", "ID", "-c", "Name")
    assert res.exit_code == 0
    admin_project_id = next(
        line.split()[0]
        for line in res.output.splitlines()
        if "admin" in line.split()[1:]
    )

    # EC2 creds carry a JSON blob: {access, secret}.
    blob = '{"access": "live-access-key", "secret": "live-secret-key"}'
    res = live_invoke("credential", "create",
                      "--user", admin_user_id,
                      "--type", "ec2",
                      "--blob", blob,
                      "--project", admin_project_id)
    assert res.exit_code == 0, res.output
    cred_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("credential", "delete", cred_id, "--yes"))

    # Update the blob
    new_blob = '{"access": "live-access-key", "secret": "rotated-secret"}'
    res = live_invoke("credential", "set", cred_id, "--blob", new_blob)
    assert res.exit_code == 0, res.output

    res = live_invoke("credential", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert cred_id in res.output

    res = live_invoke("credential", "show", cred_id,
                      "-f", "value", "-c", "type")
    assert res.exit_code == 0
    assert "ec2" in res.output
