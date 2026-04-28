"""Live e2e: Nova compute (flavors, keypairs)."""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_flavor_create_show_delete(live_invoke, cleanup, live_name):
    name = live_name("flavor")

    res = live_invoke("flavor", "create", name,
                      "--vcpus", "1", "--ram", "64", "--disk", "1")
    assert res.exit_code == 0, res.output
    flavor_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("flavor", "delete", flavor_id, "--yes"))

    res = live_invoke("flavor", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert flavor_id in res.output

    res = live_invoke("flavor", "show", flavor_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert name in res.output


def test_keypair_create_delete(live_invoke, cleanup, live_name, tmp_path):
    name = live_name("kp")
    key_path = tmp_path / f"{name}.pem"

    res = live_invoke("keypair", "create", name, "--save-to", str(key_path))
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", name, "--yes"))

    assert key_path.exists()
    assert key_path.stat().st_mode & 0o777 == 0o600

    res = live_invoke("keypair", "list", "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output
