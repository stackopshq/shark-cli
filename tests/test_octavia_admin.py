"""Tests for Octavia admin commands: set, stats, l7policy, l7rule, amphora, member/hm/pool/listener set."""

from __future__ import annotations

import pytest

LB     = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LIST   = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
POOL   = "cccccccc-cccc-cccc-cccc-cccccccccccc"
MEMBER = "dddddddd-dddd-dddd-dddd-dddddddddddd"
HM     = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
L7POL  = "ffffffff-ffff-ffff-ffff-ffffffffffff"
L7RUL  = "11111111-1111-1111-1111-111111111111"
AMPH   = "22222222-2222-2222-2222-222222222222"
OCTAVIA = "https://octavia.example.com"


def _oct(mock_client):
    mock_client.load_balancer_url = OCTAVIA
    return mock_client


# ══════════════════════════════════════════════════════════════════════════
#  loadbalancer set / stats-show / status-show
# ══════════════════════════════════════════════════════════════════════════

class TestLoadBalancerSet:

    def test_set_name(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "set", LB, "--name", "new-lb"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["loadbalancer"]
        assert body["name"] == "new-lb"

    def test_set_enable(self, invoke, mock_client):
        _oct(mock_client)
        invoke(["loadbalancer", "set", LB, "--enable"])
        body = mock_client.put.call_args[1]["json"]["loadbalancer"]
        assert body["admin_state_up"] is True

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "set", LB])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        invoke(["loadbalancer", "set", LB, "--name", "x"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2/lbaas/loadbalancers/{LB}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "set", "--help"]).exit_code == 0


class TestLoadBalancerStatsShow:

    def test_stats(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"stats": {
            "active_connections": 10, "bytes_in": 1000, "bytes_out": 2000,
            "request_errors": 0, "total_connections": 100,
        }}
        result = invoke(["loadbalancer", "stats-show", LB])
        assert result.exit_code == 0
        assert "1000" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"stats": {}}
        invoke(["loadbalancer", "stats-show", LB])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/lbaas/loadbalancers/{LB}/stats" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "stats-show", "--help"]).exit_code == 0


class TestLoadBalancerStatusShow:

    def test_status(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"statuses": {"loadbalancer": {"id": LB}}}
        result = invoke(["loadbalancer", "status-show", LB])
        assert result.exit_code == 0

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"statuses": {}}
        invoke(["loadbalancer", "status-show", LB])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/lbaas/loadbalancers/{LB}/statuses" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "status-show", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  listener-set
# ══════════════════════════════════════════════════════════════════════════

class TestListenerSet:

    def test_set_name(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "listener-set", LIST, "--name", "new-name"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["listener"]
        assert body["name"] == "new-name"

    def test_set_connection_limit(self, invoke, mock_client):
        _oct(mock_client)
        invoke(["loadbalancer", "listener-set", LIST, "--connection-limit", "1000"])
        body = mock_client.put.call_args[1]["json"]["listener"]
        assert body["connection_limit"] == 1000

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "listener-set", LIST])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "listener-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  pool-set
# ══════════════════════════════════════════════════════════════════════════

class TestPoolSet:

    def test_set_algorithm(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "pool-set", POOL,
                         "--algorithm", "LEAST_CONNECTIONS"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["pool"]
        assert body["lb_algorithm"] == "LEAST_CONNECTIONS"

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "pool-set", POOL])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "pool-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  member-show / member-set
# ══════════════════════════════════════════════════════════════════════════

class TestMemberShow:

    def test_show(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"member": {
            "id": MEMBER, "address": "10.0.0.1", "protocol_port": 80,
            "weight": 1, "operating_status": "ONLINE",
            "provisioning_status": "ACTIVE", "admin_state_up": True,
            "subnet_id": "", "name": "", "created_at": "", "updated_at": "",
        }}
        result = invoke(["loadbalancer", "member-show", POOL, MEMBER])
        assert result.exit_code == 0
        assert "ONLINE" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"member": {}}
        invoke(["loadbalancer", "member-show", POOL, MEMBER])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/lbaas/pools/{POOL}/members/{MEMBER}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "member-show", "--help"]).exit_code == 0


class TestMemberSet:

    def test_set_weight(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "member-set", POOL, MEMBER, "--weight", "5"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["member"]
        assert body["weight"] == 5

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "member-set", POOL, MEMBER])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        invoke(["loadbalancer", "member-set", POOL, MEMBER, "--weight", "3"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2/lbaas/pools/{POOL}/members/{MEMBER}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "member-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  healthmonitor-show / healthmonitor-set
# ══════════════════════════════════════════════════════════════════════════

class TestHealthMonitorShow:

    def test_show(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"healthmonitor": {
            "id": HM, "name": "my-hm", "type": "HTTP", "pool_id": POOL,
            "delay": 5, "timeout": 3, "max_retries": 3,
            "url_path": "/health", "expected_codes": "200",
            "provisioning_status": "ACTIVE", "admin_state_up": True,
            "created_at": "", "updated_at": "",
        }}
        result = invoke(["loadbalancer", "healthmonitor-show", HM])
        assert result.exit_code == 0
        assert "HTTP" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"healthmonitor": {}}
        invoke(["loadbalancer", "healthmonitor-show", HM])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/lbaas/healthmonitors/{HM}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "healthmonitor-show", "--help"]).exit_code == 0


class TestHealthMonitorSet:

    def test_set_delay(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "healthmonitor-set", HM, "--delay", "10"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["healthmonitor"]
        assert body["delay"] == 10

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "healthmonitor-set", HM])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "healthmonitor-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  l7policy CRUD
# ══════════════════════════════════════════════════════════════════════════

class TestL7PolicyList:

    def _pol(self, **kw):
        return {"id": L7POL, "name": "my-policy", "action": "REJECT",
                "listener_id": LIST, "position": 1,
                "provisioning_status": "ACTIVE", **kw}

    def test_list(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"l7policies": [self._pol()]}
        result = invoke(["loadbalancer", "l7policy-list"])
        assert result.exit_code == 0
        assert "REJE" in result.output

    def test_list_empty(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"l7policies": []}
        result = invoke(["loadbalancer", "l7policy-list"])
        assert "No L7" in result.output

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7policy-list", "--help"]).exit_code == 0


class TestL7PolicyShow:

    def test_show(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"l7policy": {
            "id": L7POL, "name": "pol", "listener_id": LIST,
            "action": "REJECT", "redirect_pool_id": "", "redirect_url": "",
            "redirect_prefix": "", "position": 1,
            "provisioning_status": "ACTIVE", "admin_state_up": True, "created_at": "",
        }}
        result = invoke(["loadbalancer", "l7policy-show", L7POL])
        assert result.exit_code == 0
        assert "REJECT" in result.output

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7policy-show", "--help"]).exit_code == 0


class TestL7PolicyCreate:

    def test_create_reject(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"l7policy": {"id": L7POL}}
        result = invoke(["loadbalancer", "l7policy-create",
                         "--listener-id", LIST, "--action", "REJECT"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["l7policy"]
        assert body["action"] == "REJECT"
        assert body["listener_id"] == LIST

    def test_create_redirect_pool(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"l7policy": {"id": L7POL}}
        invoke(["loadbalancer", "l7policy-create",
                "--listener-id", LIST,
                "--action", "REDIRECT_TO_POOL",
                "--redirect-pool-id", POOL])
        body = mock_client.post.call_args[1]["json"]["l7policy"]
        assert body["redirect_pool_id"] == POOL

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"l7policy": {"id": L7POL}}
        invoke(["loadbalancer", "l7policy-create",
                "--listener-id", LIST, "--action", "REJECT"])
        url = mock_client.post.call_args[0][0]
        assert "/v2/lbaas/l7policies" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7policy-create", "--help"]).exit_code == 0


class TestL7PolicySet:

    def test_set_action(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7policy-set", L7POL, "--action", "REJECT"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["l7policy"]
        assert body["action"] == "REJECT"

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7policy-set", L7POL])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7policy-set", "--help"]).exit_code == 0


class TestL7PolicyDelete:

    def test_delete_yes(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7policy-delete", L7POL, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7policy-delete", L7POL], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7policy-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  l7rule CRUD
# ══════════════════════════════════════════════════════════════════════════

class TestL7RuleList:

    def test_list(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"rules": [
            {"id": L7RUL, "type": "PATH", "compare_type": "STARTS_WITH",
             "value": "/api", "invert": False, "provisioning_status": "ACTIVE"},
        ]}
        result = invoke(["loadbalancer", "l7rule-list", L7POL])
        assert result.exit_code == 0
        assert "PATH" in result.output

    def test_list_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"rules": []}
        invoke(["loadbalancer", "l7rule-list", L7POL])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/lbaas/l7policies/{L7POL}/rules" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7rule-list", "--help"]).exit_code == 0


class TestL7RuleShow:

    def test_show(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"rule": {
            "id": L7RUL, "type": "PATH", "compare_type": "STARTS_WITH",
            "key": "", "value": "/api", "invert": False,
            "provisioning_status": "ACTIVE", "admin_state_up": True, "created_at": "",
        }}
        result = invoke(["loadbalancer", "l7rule-show", L7POL, L7RUL])
        assert result.exit_code == 0
        assert "PATH" in result.output

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7rule-show", "--help"]).exit_code == 0


class TestL7RuleCreate:

    def test_create(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"rule": {"id": L7RUL}}
        result = invoke(["loadbalancer", "l7rule-create", L7POL,
                         "--type", "PATH",
                         "--compare-type", "STARTS_WITH",
                         "--value", "/api"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["rule"]
        assert body["type"] == "PATH"
        assert body["value"] == "/api"

    def test_create_with_invert(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"rule": {"id": L7RUL}}
        invoke(["loadbalancer", "l7rule-create", L7POL,
                "--type", "HOST_NAME",
                "--compare-type", "EQUAL_TO",
                "--value", "example.com",
                "--invert"])
        body = mock_client.post.call_args[1]["json"]["rule"]
        assert body["invert"] is True

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.post.return_value = {"rule": {"id": L7RUL}}
        invoke(["loadbalancer", "l7rule-create", L7POL,
                "--type", "PATH", "--compare-type", "REGEX", "--value", ".*"])
        url = mock_client.post.call_args[0][0]
        assert f"/v2/lbaas/l7policies/{L7POL}/rules" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7rule-create", "--help"]).exit_code == 0


class TestL7RuleSet:

    def test_set_value(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7rule-set", L7POL, L7RUL, "--value", "/new"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["rule"]
        assert body["value"] == "/new"

    def test_set_nothing(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7rule-set", L7POL, L7RUL])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        invoke(["loadbalancer", "l7rule-set", L7POL, L7RUL, "--value", "/x"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2/lbaas/l7policies/{L7POL}/rules/{L7RUL}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7rule-set", "--help"]).exit_code == 0


class TestL7RuleDelete:

    def test_delete_yes(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7rule-delete", L7POL, L7RUL, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "l7rule-delete", L7POL, L7RUL], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "l7rule-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  amphora
# ══════════════════════════════════════════════════════════════════════════

class TestAmphoraList:

    def _amph(self, **kw):
        return {"id": AMPH, "loadbalancer_id": LB, "status": "ALLOCATED",
                "role": "MASTER", "compute_id": "xxx", "ha_ip": "10.0.0.1", **kw}

    def test_list(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"amphorae": [self._amph()]}
        result = invoke(["loadbalancer", "amphora-list"])
        assert result.exit_code == 0
        assert "MAST" in result.output

    def test_list_filter_lb(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"amphorae": []}
        invoke(["loadbalancer", "amphora-list", "--lb-id", LB])
        assert mock_client.get.call_args[1]["params"]["loadbalancer_id"] == LB

    def test_list_empty(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"amphorae": []}
        result = invoke(["loadbalancer", "amphora-list"])
        assert "No amphorae" in result.output

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "amphora-list", "--help"]).exit_code == 0


class TestAmphoraShow:

    def test_show(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"amphora": {
            "id": AMPH, "loadbalancer_id": LB, "compute_id": "xxx",
            "status": "ALLOCATED", "role": "MASTER", "lb_network_ip": "10.0.0.1",
            "ha_ip": "", "ha_port_id": "", "vrrp_ip": "", "vrrp_interface": "",
            "vrrp_priority": 100, "cert_expiration": "", "created_at": "", "updated_at": "",
        }}
        result = invoke(["loadbalancer", "amphora-show", AMPH])
        assert result.exit_code == 0
        assert "MASTER" in result.output

    def test_calls_correct_url(self, invoke, mock_client):
        _oct(mock_client)
        mock_client.get.return_value = {"amphora": {}}
        invoke(["loadbalancer", "amphora-show", AMPH])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/octavia/amphorae/{AMPH}" in url

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "amphora-show", "--help"]).exit_code == 0


class TestAmphoraFailover:

    def test_failover_yes(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "amphora-failover", AMPH, "--yes"])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert f"/v2/octavia/amphorae/{AMPH}/failover" in url

    def test_failover_requires_confirm(self, invoke, mock_client):
        _oct(mock_client)
        result = invoke(["loadbalancer", "amphora-failover", AMPH], input="n\n")
        assert result.exit_code != 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["loadbalancer", "amphora-failover", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.parametrize("sub", [
        "set", "stats-show", "status-show",
        "listener-set",
        "pool-set",
        "member-show", "member-set",
        "healthmonitor-show", "healthmonitor-set",
        "l7policy-list", "l7policy-show", "l7policy-create",
        "l7policy-set", "l7policy-delete",
        "l7rule-list", "l7rule-show", "l7rule-create",
        "l7rule-set", "l7rule-delete",
        "amphora-list", "amphora-show", "amphora-failover",
    ])
    def test_subcommand_help(self, invoke, sub):
        result = invoke(["loadbalancer", sub, "--help"])
        assert result.exit_code == 0, f"'loadbalancer {sub} --help' failed: {result.output}"
