"""Live e2e: Keystone identity (project, user)."""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_project_create_show_delete(live_invoke, cleanup, live_name):
    name = live_name("proj")

    res = live_invoke("project", "create", name,
                      "--description", "live test project")
    assert res.exit_code == 0, res.output
    project_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", project_id, "--yes"))

    res = live_invoke("project", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert project_id in res.output

    res = live_invoke("project", "show", project_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert name in res.output


def test_user_create_show_delete(live_invoke, cleanup, live_name):
    name = live_name("user")

    res = live_invoke("user", "create", name, "--password", "pw")
    assert res.exit_code == 0, res.output
    user_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("user", "delete", user_id, "--yes"))

    res = live_invoke("user", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert user_id in res.output
