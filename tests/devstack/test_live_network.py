"""Live e2e: Neutron networks, subnets, security groups."""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_network_create_show_delete(live_invoke, cleanup, live_name):
    name = live_name("net")

    res = live_invoke("network", "create", name)
    assert res.exit_code == 0, res.output
    net_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "delete", net_id, "--yes"))

    res = live_invoke("network", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert net_id in res.output


def test_subnet_create_delete_on_new_network(live_invoke, cleanup, live_name):
    net_name = live_name("net")
    sub_name = live_name("sub")

    res = live_invoke("network", "create", net_name)
    assert res.exit_code == 0, res.output
    net_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "delete", net_id, "--yes"))

    res = live_invoke("network", "subnet", "create", sub_name,
                      "--network-id", net_id, "--cidr", "10.99.0.0/24")
    assert res.exit_code == 0, res.output
    sub_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "subnet", "delete", sub_id, "--yes"))

    res = live_invoke("network", "subnet", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert sub_id in res.output


def test_security_group_create_delete(live_invoke, cleanup, live_name):
    name = live_name("sg")

    res = live_invoke("security-group", "create", name,
                      "--description", "live test sg")
    assert res.exit_code == 0, res.output
    sg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", sg_id, "--yes"))

    res = live_invoke("security-group", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert sg_id in res.output
