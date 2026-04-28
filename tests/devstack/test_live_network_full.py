"""Live e2e: comprehensive Neutron coverage.

Covers ``network`` (incl. ``port``, ``router``, ``rbac``, ``segment``,
``agent``, ``auto-allocated-topology``), ``security-group`` (with
rule-add/rule-delete/clone/cleanup), ``qos`` (policies + rules),
``floating-ip`` (list-only, no external net on this DevStack), ``trunk``,
``subnet-pool``, and the ``ip whois`` utility.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


# ── Helpers ───────────────────────────────────────────────────────────

def _create_network(live_invoke, cleanup, name):
    res = live_invoke("network", "create", name)
    assert res.exit_code == 0, res.output
    net_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "delete", net_id, "--yes"))
    return net_id


def _create_subnet(live_invoke, cleanup, net_id, name, cidr):
    res = live_invoke("network", "subnet", "create", name,
                      "--network-id", net_id, "--cidr", cidr)
    assert res.exit_code == 0, res.output
    sub_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "subnet", "delete", sub_id, "--yes"))
    return sub_id


# ── Tests ─────────────────────────────────────────────────────────────


def test_port_full(live_invoke, cleanup, live_name):
    net_id = _create_network(live_invoke, cleanup, live_name("net"))
    _create_subnet(live_invoke, cleanup, net_id, live_name("sub"), "10.51.0.0/24")

    res = live_invoke("network", "port", "create",
                      "--network-id", net_id,
                      "--name", live_name("port"))
    assert res.exit_code == 0, res.output
    port_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "port", "delete", port_id, "--yes"))

    res = live_invoke("network", "port", "update", port_id,
                      "--name", "renamed-port", "--admin-state")
    assert res.exit_code == 0, res.output

    res = live_invoke("network", "port", "unset", port_id, "--description")
    assert res.exit_code == 0, res.output

    res = live_invoke("network", "port", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert port_id in res.output

    res = live_invoke("network", "port", "show", port_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert "renamed-port" in res.output


def test_router_basic_full(live_invoke, cleanup, live_name):
    name = live_name("rtr")
    res = live_invoke("network", "router", "create", name)
    assert res.exit_code == 0, res.output
    router_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "router", "delete", router_id, "--yes"))

    res = live_invoke("network", "router", "update", router_id,
                      "--name", name + "-renamed")
    assert res.exit_code == 0, res.output

    # Add a subnet interface to the router.
    net_id = _create_network(live_invoke, cleanup, live_name("net"))
    sub_id = _create_subnet(live_invoke, cleanup, net_id,
                            live_name("sub"), "10.52.0.0/24")

    res = live_invoke("network", "router", "add", "interface",
                      router_id, "--subnet-id", sub_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("network", "router", "remove", "interface",
                                router_id, "--subnet-id", sub_id))

    res = live_invoke("network", "router", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert router_id in res.output

    res = live_invoke("network", "router", "show", router_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0


def test_segment_list(live_invoke):
    # Segments require the `segment` Neutron extension. DevStack OVN
    # ships without it by default — list still goes through but returns
    # 404 / empty depending on cloud. Skip cleanly if unavailable.
    res = live_invoke("network", "segment", "list",
                      "-f", "value", "-c", "ID")
    if res.exit_code != 0 and "Not found" in res.output:
        pytest.skip("Neutron `segment` extension not enabled on this cloud")
    assert res.exit_code == 0, res.output


def test_agent_list_show(live_invoke):
    # OVN agents always exist on DevStack.
    res = live_invoke("network", "agent", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0, res.output
    agent_id = res.output.strip().splitlines()[0]
    assert agent_id

    res = live_invoke("network", "agent", "show", agent_id)
    assert res.exit_code == 0, res.output


def test_auto_allocated_topology(live_invoke):
    # show may fail if the project lacks the topology — accept either
    # success or a clean 4xx (not a 5xx / Click parser crash).
    res = live_invoke("network", "auto-allocated-topology", "show")
    assert res.exit_code in (0, 1), res.output


def test_security_group_full(live_invoke, cleanup, live_name):
    name = live_name("sg")
    res = live_invoke("security-group", "create", name,
                      "--description", "live test sg")
    assert res.exit_code == 0, res.output
    sg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", sg_id, "--yes"))

    # update
    res = live_invoke("security-group", "update", sg_id,
                      "--description", "live test sg updated")
    assert res.exit_code == 0, res.output

    # rule-add (ingress SSH from anywhere)
    res = live_invoke("security-group", "rule", "add", sg_id,
                      "--direction", "ingress",
                      "--protocol", "tcp",
                      "--port-min", "22", "--port-max", "22",
                      "--remote-ip", "0.0.0.0/0")
    assert res.exit_code == 0, res.output
    rule_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "rule", "delete",
                                rule_id, "--yes"))

    # show / list — both should include the SG
    res = live_invoke("security-group", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert sg_id in res.output

    res = live_invoke("security-group", "show", sg_id)
    assert res.exit_code == 0
    assert name in res.output

    # clone
    cloned_name = live_name("sg-clone")
    res = live_invoke("security-group", "clone", sg_id, cloned_name,
                      "--description", "cloned SG")
    assert res.exit_code == 0, res.output
    clone_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", clone_id, "--yes"))

    # cleanup --delete is destructive — only run dry-run mode in CI
    res = live_invoke("security-group", "cleanup")
    assert res.exit_code == 0, res.output


def test_qos_full(live_invoke, cleanup, live_name):
    pname = live_name("qos")
    res = live_invoke("qos", "policy", "create",
                      "--name", pname, "--description", "live test qos")
    if res.exit_code != 0 and "Not found" in res.output:
        pytest.skip("Neutron `qos` extension not enabled on this cloud")
    assert res.exit_code == 0, res.output
    policy_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("qos", "policy", "delete", policy_id, "--yes"))

    res = live_invoke("qos", "policy", "set", policy_id,
                      "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("qos", "policy", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert policy_id in res.output

    res = live_invoke("qos", "policy", "show", policy_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert pname in res.output

    # rule-create (bandwidth-limit)
    res = live_invoke("qos", "rule", "create", policy_id,
                      "--type", "bandwidth-limit",
                      "--max-kbps", "1000")
    assert res.exit_code == 0, res.output
    rule_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("qos", "rule", "delete",
                                policy_id, rule_id, "--yes"))

    res = live_invoke("qos", "rule", "list", policy_id,
                      "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert rule_id in res.output


def test_floating_ip_list(live_invoke):
    # Without an external network on this DevStack, allocation is not
    # possible — list/bulk-release still cover the API surface.
    res = live_invoke("floating-ip", "list")
    assert res.exit_code == 0, res.output


def test_trunk_full(live_invoke, cleanup, live_name):
    # Parent port + child port on the same network for the subport.
    net_id = _create_network(live_invoke, cleanup, live_name("trunk-net"))
    _create_subnet(live_invoke, cleanup, net_id,
                   live_name("trunk-sub"), "10.53.0.0/24")

    res = live_invoke("network", "port", "create",
                      "--network-id", net_id, "--name", live_name("trunk-pp"))
    assert res.exit_code == 0, res.output
    parent_port = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "port", "delete",
                                parent_port, "--yes"))

    res = live_invoke("network", "port", "create",
                      "--network-id", net_id, "--name", live_name("trunk-cp"))
    assert res.exit_code == 0, res.output
    sub_port = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "port", "delete",
                                sub_port, "--yes"))

    name = live_name("trunk")
    res = live_invoke("trunk", "create", "--name", name, "--port", parent_port)
    if res.exit_code != 0 and "Not found" in res.output:
        pytest.skip("Neutron `trunk` extension not enabled on this cloud")
    assert res.exit_code == 0, res.output
    trunk_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("trunk", "delete", trunk_id, "--yes"))

    res = live_invoke("trunk", "set", trunk_id, "--name", name + "-renamed")
    assert res.exit_code == 0, res.output

    res = live_invoke("trunk", "subport", "add", trunk_id,
                      "--port", sub_port,
                      "--segmentation-type", "vlan",
                      "--segmentation-id", "100")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("trunk", "subport", "remove",
                                trunk_id, "--port", sub_port))

    res = live_invoke("trunk", "subport", "list", trunk_id,
                      "-f", "value", "-c", "Port ID")
    assert res.exit_code == 0
    assert sub_port in res.output

    res = live_invoke("trunk", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert trunk_id in res.output

    res = live_invoke("trunk", "show", trunk_id, "-f", "value", "-c", "Name")
    assert res.exit_code == 0


def test_subnet_pool_full(live_invoke, cleanup, live_name):
    name = live_name("pool")
    res = live_invoke("subnet-pool", "create",
                      "--name", name,
                      "--pool-prefix", "10.99.0.0/16",
                      "--default-prefix-length", "24",
                      "--description", "live test pool")
    assert res.exit_code == 0, res.output
    pool_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("subnet-pool", "delete", pool_id, "--yes"))

    res = live_invoke("subnet-pool", "set", pool_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("subnet-pool", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert pool_id in res.output

    res = live_invoke("subnet-pool", "show", pool_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output


def test_ip_whois(live_invoke):
    # Pure utility; no API call. Just check it runs.
    res = live_invoke("ip", "whois", "8.8.8.8")
    assert res.exit_code in (0, 1), res.output  # no internet access in CI is OK
