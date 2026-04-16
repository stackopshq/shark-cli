"""Tests for Neutron admin commands: subnet-update, agents, rbac, subnet-pool, qos, trunk."""

from __future__ import annotations

import pytest

NET = "https://neutron.example.com"
SUBNET = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
AGENT  = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
RBAC   = "cccccccc-cccc-cccc-cccc-cccccccccccc"
POOL   = "dddddddd-dddd-dddd-dddd-dddddddddddd"
POLICY = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
RULE   = "ffffffff-ffff-ffff-ffff-ffffffffffff"
TRUNK  = "11111111-1111-1111-1111-111111111111"
PORT   = "22222222-2222-2222-2222-222222222222"
PORT2  = "33333333-3333-3333-3333-333333333333"


def _net(mock_client):
    mock_client.network_url = NET
    return mock_client


# ══════════════════════════════════════════════════════════════════════════
#  network subnet-update
# ══════════════════════════════════════════════════════════════════════════

class TestSubnetUpdate:

    def test_update_name(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "subnet-update", SUBNET, "--name", "new-name"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["subnet"]
        assert body["name"] == "new-name"

    def test_update_dns(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "subnet-update", SUBNET,
                         "--dns-nameserver", "8.8.8.8",
                         "--dns-nameserver", "1.1.1.1"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["subnet"]
        assert "8.8.8.8" in body["dns_nameservers"]
        assert "1.1.1.1" in body["dns_nameservers"]

    def test_enable_dhcp(self, invoke, mock_client):
        _net(mock_client)
        invoke(["network", "subnet-update", SUBNET, "--enable-dhcp"])
        body = mock_client.put.call_args[1]["json"]["subnet"]
        assert body["enable_dhcp"] is True

    def test_disable_dhcp(self, invoke, mock_client):
        _net(mock_client)
        invoke(["network", "subnet-update", SUBNET, "--disable-dhcp"])
        body = mock_client.put.call_args[1]["json"]["subnet"]
        assert body["enable_dhcp"] is False

    def test_nothing_to_update(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "subnet-update", SUBNET])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        invoke(["network", "subnet-update", SUBNET, "--name", "x"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2.0/subnets/{SUBNET}" in url

    def test_help(self, invoke):
        assert invoke(["network", "subnet-update", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  network agent-list / show / set / delete
# ══════════════════════════════════════════════════════════════════════════

class TestNetworkAgentList:

    def _agent(self, **kw):
        return {"id": AGENT, "agent_type": "L3 agent", "host": "ctrl1",
                "topic": "l3_agent", "alive": True, "admin_state_up": True, **kw}

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"agents": [self._agent()]}
        result = invoke(["network", "agent-list"])
        assert result.exit_code == 0
        assert "L3" in result.output

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"agents": []}
        result = invoke(["network", "agent-list"])
        assert "No agents" in result.output

    def test_help(self, invoke):
        assert invoke(["network", "agent-list", "--help"]).exit_code == 0


class TestNetworkAgentShow:

    def test_show(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"agent": {
            "id": AGENT, "agent_type": "L3 agent", "host": "ctrl1",
            "alive": True, "admin_state_up": True, "topic": "l3_agent",
        }}
        result = invoke(["network", "agent-show", AGENT])
        assert result.exit_code == 0
        assert "L3" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"agent": {}}
        invoke(["network", "agent-show", AGENT])
        url = mock_client.get.call_args[0][0]
        assert f"/v2.0/agents/{AGENT}" in url

    def test_help(self, invoke):
        assert invoke(["network", "agent-show", "--help"]).exit_code == 0


class TestNetworkAgentSet:

    def test_disable(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "agent-set", AGENT, "--disable"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["agent"]
        assert body["admin_state_up"] is False

    def test_enable(self, invoke, mock_client):
        _net(mock_client)
        invoke(["network", "agent-set", AGENT, "--enable"])
        body = mock_client.put.call_args[1]["json"]["agent"]
        assert body["admin_state_up"] is True

    def test_help(self, invoke):
        assert invoke(["network", "agent-set", "--help"]).exit_code == 0


class TestNetworkAgentDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "agent-delete", AGENT, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        assert f"/v2.0/agents/{AGENT}" in mock_client.delete.call_args[0][0]

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "agent-delete", AGENT], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["network", "agent-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  network rbac-list / show / create / delete
# ══════════════════════════════════════════════════════════════════════════

class TestNetworkRbacList:

    def _rbac(self, **kw):
        return {"id": RBAC, "object_type": "network", "object_id": PORT,
                "action": "access_as_shared", "target_project_id": "*", **kw}

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"rbac_policies": [self._rbac()]}
        result = invoke(["network", "rbac-list"])
        assert result.exit_code == 0
        assert "network" in result.output

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"rbac_policies": []}
        result = invoke(["network", "rbac-list"])
        assert "No RBAC" in result.output

    def test_help(self, invoke):
        assert invoke(["network", "rbac-list", "--help"]).exit_code == 0


class TestNetworkRbacShow:

    def test_show(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"rbac_policy": {
            "id": RBAC, "object_type": "network", "object_id": PORT,
            "action": "access_as_shared", "target_project_id": "*",
        }}
        result = invoke(["network", "rbac-show", RBAC])
        assert result.exit_code == 0
        assert "network" in result.output

    def test_help(self, invoke):
        assert invoke(["network", "rbac-show", "--help"]).exit_code == 0


class TestNetworkRbacCreate:

    def test_create(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"rbac_policy": {"id": RBAC}}
        result = invoke(["network", "rbac-create",
                         "--object-type", "network",
                         "--object", PORT,
                         "--target-project", "*",
                         "--action", "access_as_shared"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["rbac_policy"]
        assert body["object_type"] == "network"
        assert body["action"] == "access_as_shared"

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"rbac_policy": {"id": RBAC}}
        invoke(["network", "rbac-create",
                "--object-type", "network",
                "--object", PORT,
                "--target-project", "*",
                "--action", "access_as_shared"])
        url = mock_client.post.call_args[0][0]
        assert "/v2.0/rbac-policies" in url

    def test_help(self, invoke):
        assert invoke(["network", "rbac-create", "--help"]).exit_code == 0


class TestNetworkRbacDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "rbac-delete", RBAC, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["network", "rbac-delete", RBAC], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["network", "rbac-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  subnet-pool
# ══════════════════════════════════════════════════════════════════════════

class TestSubnetPoolList:

    def _pool(self, **kw):
        return {"id": POOL, "name": "my-pool", "prefixes": ["10.0.0.0/8"],
                "default_prefixlen": 24, "min_prefixlen": 8, "max_prefixlen": 32,
                "shared": False, "is_default": False, **kw}

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"subnetpools": [self._pool()]}
        result = invoke(["subnet-pool", "list"])
        assert result.exit_code == 0
        assert "Subnet Pools" in result.output

    def test_list_shared_filter(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"subnetpools": []}
        invoke(["subnet-pool", "list", "--shared"])
        assert mock_client.get.call_args[1]["params"].get("shared") is True

    def test_list_default_filter(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"subnetpools": []}
        invoke(["subnet-pool", "list", "--default"])
        assert mock_client.get.call_args[1]["params"].get("is_default") is True

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"subnetpools": []}
        result = invoke(["subnet-pool", "list"])
        assert "No subnet pools" in result.output

    def test_help(self, invoke):
        assert invoke(["subnet-pool", "list", "--help"]).exit_code == 0


class TestSubnetPoolShow:

    def test_show(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"subnetpool": {
            "id": POOL, "name": "my-pool", "prefixes": ["10.0.0.0/8"],
            "default_prefixlen": 24, "min_prefixlen": 8, "max_prefixlen": 32,
            "shared": False, "is_default": False, "ip_version": 4, "description": "",
        }}
        result = invoke(["subnet-pool", "show", POOL])
        assert result.exit_code == 0
        assert "my-pool" in result.output

    def test_help(self, invoke):
        assert invoke(["subnet-pool", "show", "--help"]).exit_code == 0


class TestSubnetPoolCreate:

    def test_create(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"subnetpool": {"id": POOL}}
        result = invoke(["subnet-pool", "create",
                         "--name", "my-pool",
                         "--pool-prefix", "10.0.0.0/8",
                         "--default-prefix-length", "24"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["subnetpool"]
        assert body["name"] == "my-pool"
        assert "10.0.0.0/8" in body["prefixes"]
        assert body["default_prefixlen"] == 24

    def test_create_multiple_prefixes(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"subnetpool": {"id": POOL}}
        invoke(["subnet-pool", "create", "--name", "p",
                "--pool-prefix", "10.0.0.0/8",
                "--pool-prefix", "192.168.0.0/16"])
        body = mock_client.post.call_args[1]["json"]["subnetpool"]
        assert len(body["prefixes"]) == 2

    def test_help(self, invoke):
        assert invoke(["subnet-pool", "create", "--help"]).exit_code == 0


class TestSubnetPoolSet:

    def test_set_name(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["subnet-pool", "set", POOL, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["subnetpool"]
        assert body["name"] == "renamed"

    def test_set_nothing(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["subnet-pool", "set", POOL])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["subnet-pool", "set", "--help"]).exit_code == 0


class TestSubnetPoolDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["subnet-pool", "delete", POOL, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["subnet-pool", "delete", POOL], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["subnet-pool", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  qos policy CRUD
# ══════════════════════════════════════════════════════════════════════════

class TestQosPolicyList:

    def _policy(self, **kw):
        return {"id": POLICY, "name": "my-qos", "shared": False,
                "is_default": False, "description": "", **kw}

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"policies": [self._policy()]}
        result = invoke(["qos", "policy-list"])
        assert result.exit_code == 0
        assert "my-qos" in result.output

    def test_list_shared_filter(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"policies": []}
        invoke(["qos", "policy-list", "--shared"])
        assert mock_client.get.call_args[1]["params"].get("shared") is True

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"policies": []}
        result = invoke(["qos", "policy-list"])
        assert "No QoS" in result.output

    def test_help(self, invoke):
        assert invoke(["qos", "policy-list", "--help"]).exit_code == 0


class TestQosPolicyShow:

    def test_show(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"policy": {
            "id": POLICY, "name": "my-qos", "shared": False,
            "is_default": False, "description": "", "project_id": "abc",
        }}
        result = invoke(["qos", "policy-show", POLICY])
        assert result.exit_code == 0
        assert "my-qos" in result.output

    def test_help(self, invoke):
        assert invoke(["qos", "policy-show", "--help"]).exit_code == 0


class TestQosPolicyCreate:

    def test_create(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"policy": {"id": POLICY}}
        result = invoke(["qos", "policy-create", "--name", "my-qos"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["policy"]
        assert body["name"] == "my-qos"

    def test_create_shared(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"policy": {"id": POLICY}}
        invoke(["qos", "policy-create", "--name", "q", "--shared"])
        body = mock_client.post.call_args[1]["json"]["policy"]
        assert body["shared"] is True

    def test_help(self, invoke):
        assert invoke(["qos", "policy-create", "--help"]).exit_code == 0


class TestQosPolicySet:

    def test_set_name(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "policy-set", POLICY, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["policy"]
        assert body["name"] == "renamed"

    def test_set_nothing(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "policy-set", POLICY])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["qos", "policy-set", "--help"]).exit_code == 0


class TestQosPolicyDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "policy-delete", POLICY, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "policy-delete", POLICY], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["qos", "policy-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  qos rules
# ══════════════════════════════════════════════════════════════════════════

class TestQosRuleList:

    def test_list_bandwidth(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"bandwidth_limit_rules": [
            {"id": RULE, "max_kbps": 1000, "max_burst_kbps": 200, "direction": "egress"}
        ]}
        result = invoke(["qos", "rule-list", POLICY])
        assert result.exit_code == 0
        assert "1000" in result.output

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"bandwidth_limit_rules": []}
        result = invoke(["qos", "rule-list", POLICY])
        assert result.exit_code == 0

    def test_list_dscp(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"dscp_marking_rules": [
            {"id": RULE, "dscp_mark": 14}
        ]}
        result = invoke(["qos", "rule-list", POLICY, "--type", "dscp-marking"])
        assert result.exit_code == 0

    def test_help(self, invoke):
        assert invoke(["qos", "rule-list", "--help"]).exit_code == 0


class TestQosRuleCreate:

    def test_create_bandwidth_limit(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"bandwidth_limit_rule": {"id": RULE}}
        result = invoke(["qos", "rule-create", POLICY,
                         "--type", "bandwidth-limit",
                         "--max-kbps", "1000"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["bandwidth_limit_rule"]
        assert body["max_kbps"] == 1000

    def test_create_bandwidth_requires_max_kbps(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "rule-create", POLICY, "--type", "bandwidth-limit"])
        assert result.exit_code != 0

    def test_create_dscp_marking(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"dscp_marking_rule": {"id": RULE}}
        result = invoke(["qos", "rule-create", POLICY,
                         "--type", "dscp-marking", "--dscp-mark", "14"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["dscp_marking_rule"]
        assert body["dscp_mark"] == 14

    def test_create_dscp_requires_mark(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "rule-create", POLICY, "--type", "dscp-marking"])
        assert result.exit_code != 0

    def test_create_minimum_bandwidth(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"minimum_bandwidth_rule": {"id": RULE}}
        result = invoke(["qos", "rule-create", POLICY,
                         "--type", "minimum-bandwidth", "--min-kbps", "500"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["minimum_bandwidth_rule"]
        assert body["min_kbps"] == 500

    def test_help(self, invoke):
        assert invoke(["qos", "rule-create", "--help"]).exit_code == 0


class TestQosRuleDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "rule-delete", POLICY, RULE, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["qos", "rule-delete", POLICY, RULE], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        invoke(["qos", "rule-delete", POLICY, RULE, "--yes"])
        url = mock_client.delete.call_args[0][0]
        assert f"/qos/policies/{POLICY}" in url
        assert RULE in url

    def test_help(self, invoke):
        assert invoke(["qos", "rule-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  trunk
# ══════════════════════════════════════════════════════════════════════════

class TestTrunkList:

    def _trunk(self, **kw):
        return {"id": TRUNK, "name": "my-trunk", "port_id": PORT,
                "status": "ACTIVE", "admin_state_up": True, **kw}

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"trunks": [self._trunk()]}
        result = invoke(["trunk", "list"])
        assert result.exit_code == 0
        assert "ACTIVE" in result.output

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"trunks": []}
        result = invoke(["trunk", "list"])
        assert "No trunks" in result.output

    def test_help(self, invoke):
        assert invoke(["trunk", "list", "--help"]).exit_code == 0


class TestTrunkShow:

    def test_show(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"trunk": {
            "id": TRUNK, "name": "my-trunk", "port_id": PORT,
            "status": "ACTIVE", "admin_state_up": True,
            "description": "", "project_id": "abc", "sub_ports": [],
        }}
        result = invoke(["trunk", "show", TRUNK])
        assert result.exit_code == 0
        assert "ACTIVE" in result.output

    def test_help(self, invoke):
        assert invoke(["trunk", "show", "--help"]).exit_code == 0


class TestTrunkCreate:

    def test_create(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"trunk": {"id": TRUNK}}
        result = invoke(["trunk", "create", "--port", PORT, "--name", "my-trunk"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["trunk"]
        assert body["port_id"] == PORT
        assert body["name"] == "my-trunk"

    def test_create_disabled(self, invoke, mock_client):
        _net(mock_client)
        mock_client.post.return_value = {"trunk": {"id": TRUNK}}
        invoke(["trunk", "create", "--port", PORT, "--disable"])
        body = mock_client.post.call_args[1]["json"]["trunk"]
        assert body["admin_state_up"] is False

    def test_help(self, invoke):
        assert invoke(["trunk", "create", "--help"]).exit_code == 0


class TestTrunkSet:

    def test_set_name(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "set", TRUNK, "--name", "new-name"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["trunk"]
        assert body["name"] == "new-name"

    def test_set_nothing(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "set", TRUNK])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["trunk", "set", "--help"]).exit_code == 0


class TestTrunkDelete:

    def test_delete_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "delete", TRUNK, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "delete", TRUNK], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["trunk", "delete", "--help"]).exit_code == 0


class TestTrunkSubportList:

    def test_list(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"sub_ports": [
            {"port_id": PORT2, "segmentation_type": "vlan", "segmentation_id": 100}
        ]}
        result = invoke(["trunk", "subport-list", TRUNK])
        assert result.exit_code == 0
        assert "vlan" in result.output
        assert "100" in result.output

    def test_list_empty(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"sub_ports": []}
        result = invoke(["trunk", "subport-list", TRUNK])
        assert "No sub-ports" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        mock_client.get.return_value = {"sub_ports": []}
        invoke(["trunk", "subport-list", TRUNK])
        url = mock_client.get.call_args[0][0]
        assert f"/v2.0/trunks/{TRUNK}/get_subports" in url

    def test_help(self, invoke):
        assert invoke(["trunk", "subport-list", "--help"]).exit_code == 0


class TestTrunkAddSubport:

    def test_add(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "add-subport", TRUNK,
                         "--port", PORT2,
                         "--segmentation-id", "100"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["sub_ports"][0]
        assert body["port_id"] == PORT2
        assert body["segmentation_id"] == 100

    def test_add_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        invoke(["trunk", "add-subport", TRUNK,
                "--port", PORT2, "--segmentation-id", "100"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2.0/trunks/{TRUNK}/add_subports" in url

    def test_help(self, invoke):
        assert invoke(["trunk", "add-subport", "--help"]).exit_code == 0


class TestTrunkRemoveSubport:

    def test_remove_yes(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "remove-subport", TRUNK, "--port", PORT2, "--yes"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["sub_ports"][0]
        assert body["port_id"] == PORT2

    def test_remove_requires_confirm(self, invoke, mock_client):
        _net(mock_client)
        result = invoke(["trunk", "remove-subport", TRUNK, "--port", PORT2], input="n\n")
        assert result.exit_code != 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _net(mock_client)
        invoke(["trunk", "remove-subport", TRUNK, "--port", PORT2, "--yes"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2.0/trunks/{TRUNK}/remove_subports" in url

    def test_help(self, invoke):
        assert invoke(["trunk", "remove-subport", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════

class TestRegistration:

    def test_subnet_pool_registered(self, invoke):
        assert invoke(["subnet-pool", "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete"])
    def test_subnet_pool_subcommands(self, invoke, sub):
        assert invoke(["subnet-pool", sub, "--help"]).exit_code == 0

    def test_qos_registered(self, invoke):
        assert invoke(["qos", "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["policy-list", "policy-show", "policy-create",
                                     "policy-set", "policy-delete",
                                     "rule-list", "rule-create", "rule-delete"])
    def test_qos_subcommands(self, invoke, sub):
        assert invoke(["qos", sub, "--help"]).exit_code == 0

    def test_trunk_registered(self, invoke):
        assert invoke(["trunk", "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["list", "show", "create", "set", "delete",
                                     "subport-list", "add-subport", "remove-subport"])
    def test_trunk_subcommands(self, invoke, sub):
        assert invoke(["trunk", sub, "--help"]).exit_code == 0

    def test_network_agent_subcommands(self, invoke):
        for sub in ["agent-list", "agent-show", "agent-set", "agent-delete"]:
            result = invoke(["network", sub, "--help"])
            assert result.exit_code == 0, f"network {sub} --help failed"

    def test_network_rbac_subcommands(self, invoke):
        for sub in ["rbac-list", "rbac-show", "rbac-create", "rbac-delete"]:
            result = invoke(["network", sub, "--help"])
            assert result.exit_code == 0, f"network {sub} --help failed"

    def test_network_subnet_update(self, invoke):
        assert invoke(["network", "subnet-update", "--help"]).exit_code == 0
