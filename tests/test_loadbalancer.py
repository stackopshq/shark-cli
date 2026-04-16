"""Tests for ``orca loadbalancer`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

LB_ID = "11112222-3333-4444-5555-666677778888"
LISTENER_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
POOL_ID = "22223333-4444-5555-6666-777788889999"
MEMBER_ID = "33334444-5555-6666-7777-888899990000"
HM_ID = "44445555-6666-7777-8888-999900001111"
SUBNET_ID = "55556666-7777-8888-9999-000011112222"


def _lb(lb_id=LB_ID, name="my-lb", vip="10.0.0.100"):
    return {
        "id": lb_id, "name": name, "vip_address": vip,
        "provisioning_status": "ACTIVE", "operating_status": "ONLINE",
        "provider": "amphora", "vip_subnet_id": SUBNET_ID,
        "vip_network_id": "net-1", "vip_port_id": "port-1",
        "admin_state_up": True, "listeners": [], "pools": [],
        "created_at": "2025-01-01", "updated_at": "2025-01-02",
    }


def _listener(lid=LISTENER_ID, name="http-listener", protocol="HTTP", port=80):
    return {
        "id": lid, "name": name, "protocol": protocol, "protocol_port": port,
        "loadbalancers": [{"id": LB_ID}], "provisioning_status": "ACTIVE",
        "operating_status": "ONLINE", "default_pool_id": POOL_ID,
        "connection_limit": -1, "admin_state_up": True,
        "created_at": "2025-01-01", "updated_at": "2025-01-02",
    }


def _pool(pid=POOL_ID, name="web-pool"):
    return {
        "id": pid, "name": name, "protocol": "HTTP",
        "lb_algorithm": "ROUND_ROBIN", "members": [{"id": MEMBER_ID}],
        "provisioning_status": "ACTIVE", "operating_status": "ONLINE",
        "session_persistence": None, "healthmonitor_id": HM_ID,
        "admin_state_up": True, "created_at": "2025-01-01", "updated_at": "2025-01-02",
    }


def _member(mid=MEMBER_ID, addr="10.0.0.10", port=8080):
    return {
        "id": mid, "name": "backend-1", "address": addr,
        "protocol_port": port, "weight": 1,
        "operating_status": "ONLINE",
    }


def _hm(hid=HM_ID, name="http-check"):
    return {
        "id": hid, "name": name, "type": "HTTP",
        "delay": 5, "timeout": 3, "pool_id": POOL_ID,
        "provisioning_status": "ACTIVE",
    }


def _setup_mock(mock_client):
    mock_client.load_balancer_url = "https://octavia.example.com"

    posted = {}
    deleted = []

    def _get(url, **kwargs):
        if f"loadbalancers/{LB_ID}" in url:
            return {"loadbalancer": _lb()}
        if "loadbalancers" in url:
            return {"loadbalancers": [_lb()]}
        if f"listeners/{LISTENER_ID}" in url:
            return {"listener": _listener()}
        if "listeners" in url:
            return {"listeners": [_listener()]}
        if f"pools/{POOL_ID}/members" in url:
            return {"members": [_member()]}
        if f"pools/{POOL_ID}" in url:
            return {"pool": _pool()}
        if "pools" in url:
            return {"pools": [_pool()]}
        if "healthmonitors" in url:
            return {"healthmonitors": [_hm()]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        if "loadbalancers" in url:
            return {"loadbalancer": {"id": "new-lb", "name": "new", "vip_address": "10.0.0.101"}}
        if "listeners" in url:
            return {"listener": {"id": "new-lis", "name": "new"}}
        if "pools" in url and "members" in url:
            return {"member": {"id": "new-mem"}}
        if "pools" in url:
            return {"pool": {"id": "new-pool", "name": "new"}}
        if "healthmonitors" in url:
            return {"healthmonitor": {"id": "new-hm", "name": "new"}}
        return {}

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.delete = _delete

    return {"posted": posted, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  loadbalancer list / show / create / delete
# ══════════════════════════════════════════════════════════════════════════


class TestLBCore:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "list"])
        assert result.exit_code == 0
        assert "my-lb" in result.output
        assert "ACTI" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.load_balancer_url = "https://octavia.example.com"
        mock_client.get = lambda url, **kw: {"loadbalancers": []}

        result = invoke(["loadbalancer", "list"])
        assert result.exit_code == 0
        assert "No load balancers found" in result.output

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "show", LB_ID])
        assert result.exit_code == 0
        assert "my-lb" in result.output

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "create", "new-lb", "--subnet-id", SUBNET_ID])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["loadbalancer"]["name"] == "new-lb"

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "delete", LB_ID, "-y"])
        assert result.exit_code == 0
        assert "deletion" in result.output.lower()
        assert len(state["deleted"]) == 1

    def test_delete_cascade(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "delete", LB_ID, "--cascade", "-y"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  Listeners
# ══════════════════════════════════════════════════════════════════════════


class TestListeners:

    def test_listener_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "listener-list"])
        assert result.exit_code == 0
        assert "HTTP" in result.output
        assert "80" in result.output

    def test_listener_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "listener-show", LISTENER_ID])
        assert result.exit_code == 0
        assert "HTTP" in result.output

    def test_listener_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "listener-create", "lis-1",
                         "--lb-id", LB_ID, "--protocol", "HTTP", "--port", "80"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_listener_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "listener-delete", LISTENER_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Pools
# ══════════════════════════════════════════════════════════════════════════


class TestPools:

    def test_pool_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "pool-list"])
        assert result.exit_code == 0
        assert "web-" in result.output

    def test_pool_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "pool-show", POOL_ID])
        assert result.exit_code == 0
        assert "ROUND_ROBIN" in result.output

    def test_pool_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "pool-create", "my-pool",
                         "--lb-id", LB_ID, "--protocol", "HTTP",
                         "--algorithm", "ROUND_ROBIN"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_pool_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "pool-delete", POOL_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Members
# ══════════════════════════════════════════════════════════════════════════


class TestMembers:

    def test_member_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "member-list", POOL_ID])
        assert result.exit_code == 0
        assert "10.0" in result.output
        assert "8080" in result.output

    def test_member_add(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "member-add", POOL_ID,
                         "--address", "10.0.0.20", "--port", "8080"])
        assert result.exit_code == 0
        assert "added" in result.output.lower()

    def test_member_remove(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "member-remove", POOL_ID, MEMBER_ID, "-y"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Health Monitors
# ══════════════════════════════════════════════════════════════════════════


class TestHealthMonitors:

    def test_hm_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["loadbalancer", "healthmonitor-list"])
        assert result.exit_code == 0
        assert "HTTP" in result.output

    def test_hm_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "healthmonitor-create", "hm-1",
                         "--pool-id", POOL_ID, "--type", "HTTP",
                         "--delay", "5", "--timeout", "3"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_hm_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["loadbalancer", "healthmonitor-delete", HM_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestLBHelp:

    def test_lb_help(self, invoke):
        result = invoke(["loadbalancer", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete",
                    "listener-list", "listener-create",
                    "pool-list", "pool-create",
                    "member-list", "member-add",
                    "healthmonitor-list", "healthmonitor-create"):
            assert cmd in result.output

    def test_member_add_help(self, invoke):
        result = invoke(["loadbalancer", "member-add", "--help"])
        assert result.exit_code == 0
        assert "--address" in result.output
        assert "--port" in result.output
