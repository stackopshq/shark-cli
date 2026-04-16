"""Tests for compute commands (hypervisor, aggregate, availability-zone, limits, server-group)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

SERVER_ID   = "11112222-3333-4444-5555-666677778888"
FLAVOR_ID   = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
AGG_ID      = "11"
HV_ID       = "21"
SG_GROUP_ID = "gggg0000-1111-2222-3333-444455556666"


# ── helpers ────────────────────────────────────────────────────────────────

def _flavor(fid=FLAVOR_ID):
    return {
        "id": fid, "name": "m1.medium", "vcpus": 2, "ram": 4096,
        "disk": 40, "OS-FLV-EXT-DATA:ephemeral": 0, "swap": "",
        "rxtx_factor": 1.0, "os-flavor-access:is_public": True,
        "extra_specs": {"hw:cpu_policy": "shared"},
    }


def _hypervisor(hid=HV_ID):
    return {
        "id": hid, "hypervisor_hostname": "compute-01.example.com",
        "hypervisor_type": "QEMU", "hypervisor_version": 6002000,
        "state": "up", "status": "enabled",
        "vcpus": 32, "vcpus_used": 8, "memory_mb": 65536,
        "memory_mb_used": 16384, "local_gb": 1000, "local_gb_used": 200,
        "running_vms": 4, "current_workload": 0, "host_ip": "10.0.0.1",
    }


def _aggregate(aid=AGG_ID):
    return {
        "id": aid, "name": "ssd-hosts", "availability_zone": "az1",
        "hosts": ["compute-01", "compute-02"],
        "metadata": {"ssd": "true"},
        "created_at": "2025-01-01", "updated_at": None,
    }


def _server_group(gid=SG_GROUP_ID):
    return {
        "id": gid, "name": "no-same-host",
        "policies": ["anti-affinity"],
        "members": [], "project_id": "proj-1", "user_id": "user-1",
    }


def _server(sid=SERVER_ID):
    return {
        "id": sid, "name": "web-01", "status": "ACTIVE",
        "addresses": {}, "flavor": {"id": FLAVOR_ID},
        "image": {"id": "img-1"}, "key_name": "my-key",
        "security_groups": [{"name": "default"}],
        "OS-EXT-AZ:availability_zone": "az1",
        "OS-EXT-STS:task_state": None,
        "OS-EXT-STS:vm_state": "active",
        "OS-EXT-STS:power_state": 1,
        "created": "2025-01-01", "updated": "2025-01-01",
    }


def _setup_compute_mock(mock_client):
    mock_client.compute_url = "https://nova.example.com/v2.1"
    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if f"/flavors/{FLAVOR_ID}" in url:
            return {"flavor": _flavor()}
        if "/flavors/detail" in url or "/flavors" in url:
            return {"flavors": [_flavor()]}
        if f"/os-hypervisors/{HV_ID}" in url:
            return {"hypervisor": _hypervisor()}
        if "/os-hypervisors/statistics" in url:
            return {"hypervisor_statistics": {"count": 2, "vcpus": 64, "vcpus_used": 16}}
        if "/os-hypervisors" in url:
            return {"hypervisors": [_hypervisor()]}
        if f"/os-aggregates/{AGG_ID}" in url:
            return {"aggregate": _aggregate()}
        if "/os-aggregates" in url:
            return {"aggregates": [_aggregate()]}
        if "/os-availability-zone" in url:
            return {"availabilityZoneInfo": [
                {"zoneName": "az1", "zoneState": {"available": True}, "hosts": {"compute-01": {}}},
                {"zoneName": "az2", "zoneState": {"available": True}, "hosts": {}},
            ]}
        if f"/os-server-groups/{SG_GROUP_ID}" in url:
            return {"server_group": _server_group()}
        if "/os-server-groups" in url:
            return {"server_groups": [_server_group()]}
        if "/limits" in url:
            return {"limits": {"absolute": {
                "maxTotalInstances": 10, "totalInstancesUsed": 3,
                "maxTotalCores": 20, "totalCoresUsed": 6,
                "maxTotalRAMSize": 51200, "totalRAMUsed": 12288,
                "maxTotalKeypairs": 100, "totalKeyPairsUsed": 2,
            }}}
        if f"/servers/{SERVER_ID}/metadata" in url:
            return {"metadata": {"env": "prod"}}
        if f"/servers/{SERVER_ID}/tags" in url:
            return {"tags": ["web", "frontend"]}
        if f"/servers/{SERVER_ID}" in url:
            return {"server": _server()}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        if "/os-aggregates" in url and "/action" not in url:
            return {"aggregate": _aggregate()}
        if "/os-server-groups" in url:
            return {"server_group": _server_group()}
        if "/os-extra-specs" in url:
            return {"extra_specs": {"hw:cpu_policy": "dedicated"}}
        return {}

    def _put(url, **kwargs):
        put_data["last_body"] = kwargs.get("json", {})

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_data": put_data, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  Flavor (extended)
# ══════════════════════════════════════════════════════════════════════════


class TestFlavorExtended:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["flavor", "show", FLAVOR_ID])
        assert result.exit_code == 0
        assert "m1.medium" in result.output

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_compute_mock(mock_client)

        result = invoke(["flavor", "create", "m1.small",
                         "--vcpus", "1", "--ram", "2048", "--disk", "20"])
        assert result.exit_code == 0
        assert "created" in result.output

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_compute_mock(mock_client)

        result = invoke(["flavor", "delete", FLAVOR_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output

    def test_set(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["flavor", "set", FLAVOR_ID,
                         "--property", "hw:cpu_policy=dedicated"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_set_no_properties(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["flavor", "set", FLAVOR_ID])
        assert result.exit_code == 0
        assert "No properties" in result.output

    def test_unset(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_compute_mock(mock_client)

        result = invoke(["flavor", "unset", FLAVOR_ID, "--property", "hw:cpu_policy"])
        assert result.exit_code == 0
        assert "removed" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Hypervisors
# ══════════════════════════════════════════════════════════════════════════


class TestHypervisor:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["hypervisor", "list"])
        assert result.exit_code == 0
        assert "compute-01" in result.output

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["hypervisor", "show", HV_ID])
        assert result.exit_code == 0
        assert "compute-01" in result.output

    def test_stats(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["hypervisor", "stats"])
        assert result.exit_code == 0
        assert "vcpus" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Aggregates
# ══════════════════════════════════════════════════════════════════════════


class TestAggregate:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "list"])
        assert result.exit_code == 0
        assert "ssd-hosts" in result.output

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "show", AGG_ID])
        assert result.exit_code == 0
        assert "ssd-hosts" in result.output

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "create", "gpu-hosts", "--zone", "az-gpu"])
        assert result.exit_code == 0
        assert "created" in result.output

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "delete", AGG_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output

    def test_add_host(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "add-host", AGG_ID, "compute-03"])
        assert result.exit_code == 0
        assert "added" in result.output

    def test_remove_host(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "remove-host", AGG_ID, "compute-01"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_set(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "set", AGG_ID,
                         "--name", "ssd-hosts-new", "--property", "ssd=true"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_set_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["aggregate", "set", AGG_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Availability Zones
# ══════════════════════════════════════════════════════════════════════════


class TestAvailabilityZones:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["availability-zone", "list"])
        assert result.exit_code == 0
        assert "az1" in result.output
        assert "az2" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Limits
# ══════════════════════════════════════════════════════════════════════════


class TestLimits:

    def test_limits(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["limits", "show"])
        assert result.exit_code == 0
        assert "Instances" in result.output
        assert "10" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Server Groups
# ══════════════════════════════════════════════════════════════════════════


class TestServerGroups:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server-group", "list"])
        assert result.exit_code == 0
        assert "no-same-host" in result.output

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server-group", "show", SG_GROUP_ID])
        assert result.exit_code == 0
        assert "no-same-host" in result.output

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server-group", "create", "no-coloc",
                         "--policy", "anti-affinity"])
        assert result.exit_code == 0
        assert "created" in result.output

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_compute_mock(mock_client)

        result = invoke(["server-group", "delete", SG_GROUP_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Server: migrate, live-migrate, sg add/remove, set, metadata, tags
# ══════════════════════════════════════════════════════════════════════════


class TestServerNewCommands:

    def test_migrate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "migrate", SERVER_ID])
        assert result.exit_code == 0
        assert "Migration" in result.output

    def test_live_migrate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "live-migrate", SERVER_ID])
        assert result.exit_code == 0
        assert "Live migration" in result.output

    def test_add_security_group(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "add-security-group", SERVER_ID, "allow-ssh"])
        assert result.exit_code == 0
        assert "added" in result.output

    def test_remove_security_group(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "remove-security-group", SERVER_ID, "allow-ssh"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_set_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "set", SERVER_ID, "--name", "new-name"])
        assert result.exit_code == 0
        assert "renamed" in result.output

    def test_set_property(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "set", SERVER_ID, "--property", "env=prod"])
        assert result.exit_code == 0
        assert "Metadata" in result.output

    def test_set_tags(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "set", SERVER_ID, "--tag", "web"])
        assert result.exit_code == 0
        assert "Tags" in result.output

    def test_set_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "set", SERVER_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output

    def test_metadata_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "metadata-list", SERVER_ID])
        assert result.exit_code == 0
        assert "env" in result.output

    def test_tag_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_compute_mock(mock_client)

        result = invoke(["server", "tag-list", SERVER_ID])
        assert result.exit_code == 0
        assert "web" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestComputeHelp:

    def test_hypervisor_help(self, invoke):
        result = invoke(["hypervisor", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "stats"):
            assert cmd in result.output

    def test_aggregate_help(self, invoke):
        result = invoke(["aggregate", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "add-host", "remove-host", "set"):
            assert cmd in result.output

    def test_availability_zone_help(self, invoke):
        result = invoke(["availability-zone", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_limits_help(self, invoke):
        result = invoke(["limits", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output

    def test_server_group_help(self, invoke):
        result = invoke(["server-group", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete"):
            assert cmd in result.output

    def test_flavor_help(self, invoke):
        result = invoke(["flavor", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "set", "unset"):
            assert cmd in result.output
