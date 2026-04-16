"""Tests for ``orca cleanup`` command."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

def _fip(fip_id, port_id=None):
    return {"id": fip_id, "floating_ip_address": "203.0.113.1", "port_id": port_id}


def _volume(vol_id, name="vol", status="available", attachments=None):
    return {"id": vol_id, "name": name, "status": status, "attachments": attachments or []}


def _snapshot(snap_id, name="snap", created_at=None):
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    return {"id": snap_id, "name": name, "created_at": created_at}


def _port(port_id, device_id="", device_owner="", fixed_ips=None):
    return {
        "id": port_id,
        "device_id": device_id,
        "device_owner": device_owner,
        "fixed_ips": fixed_ips or [{"ip_address": "10.0.0.5"}],
    }


def _sg(sg_id, name="my-sg"):
    return {"id": sg_id, "name": name, "security_group_rules": []}


def _server(srv_id, name="web", status="ACTIVE", security_groups=None):
    return {
        "id": srv_id,
        "name": name,
        "status": status,
        "security_groups": security_groups or [{"name": "default"}],
    }


def _setup_mock(mock_client, fips=None, volumes=None, snapshots=None,
                ports=None, sgs=None, servers=None):
    fips = fips or []
    volumes = volumes or []
    snapshots = snapshots or []
    ports = ports or []
    sgs = sgs or []
    servers = servers or []

    def _get(url, **kwargs):
        if "floatingips" in url:
            return {"floatingips": fips}
        if "volumes/detail" in url:
            return {"volumes": volumes}
        if "snapshots/detail" in url:
            return {"snapshots": snapshots}
        if "/ports" in url:
            return {"ports": ports}
        if "security-groups" in url:
            return {"security_groups": sgs}
        if "servers/detail" in url:
            return {"servers": servers}
        return {}

    mock_client.get = _get
    mock_client.delete = lambda url, **kw: None
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.network_url = "https://neutron.example.com"
    mock_client.volume_url = "https://cinder.example.com/v3"


# ══════════════════════════════════════════════════════════════════════════
#  Clean project
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupClean:

    def test_no_orphans(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(
            mock_client,
            fips=[_fip("fip-1", port_id="port-1")],
            volumes=[_volume("v1", status="in-use", attachments=[{"server_id": "s1"}])],
            ports=[_port("p1", device_id="srv-1", device_owner="compute:nova")],
            sgs=[_sg("sg-1", name="default")],
            servers=[_server("s1")],
        )

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Floating IPs
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupFloatingIPs:

    def test_unassociated_fip_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, fips=[_fip("fip-1"), _fip("fip-2", port_id="port-1")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "floating-ip" in result.output
        assert "not associated" in result.output

    def test_all_fips_associated(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, fips=[_fip("fip-1", port_id="port-1")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Volumes
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupVolumes:

    def test_detached_volume_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, volumes=[_volume("v1", name="orphan-vol")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "volume" in result.output
        assert "detached" in result.output

    def test_error_volume_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, volumes=[_volume("v1", name="bad-vol", status="error")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "error state" in result.output

    def test_attached_volume_ok(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, volumes=[
            _volume("v1", status="in-use", attachments=[{"server_id": "s1"}]),
        ])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Snapshots
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupSnapshots:

    def test_old_snapshot_with_older_than_flag(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        _setup_mock(mock_client, snapshots=[_snapshot("snap-1", created_at=old_date)])

        result = invoke(["cleanup", "--older-than", "30"])
        assert result.exit_code == 0
        assert "snapshot" in result.output
        assert "old" in result.output  # "60d old"

    def test_recent_snapshot_not_flagged(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        recent = datetime.now(timezone.utc).isoformat()
        _setup_mock(mock_client, snapshots=[_snapshot("snap-1", created_at=recent)])

        result = invoke(["cleanup", "--older-than", "30"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output

    def test_snapshots_ignored_without_older_than_flag(self, invoke, config_dir, mock_client, sample_profile):
        """Without --older-than, snapshots are not scanned for age."""
        save_profile("p", sample_profile)
        set_active_profile("p")

        old_date = (datetime.now(timezone.utc) - timedelta(days=999)).isoformat()
        _setup_mock(mock_client, snapshots=[_snapshot("snap-1", created_at=old_date)])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Ports
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupPorts:

    def test_orphan_port_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, ports=[_port("p1")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "port" in result.output
        assert "no device" in result.output

    def test_port_with_device_ok(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, ports=[_port("p1", device_id="srv-1", device_owner="compute:nova")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Security groups
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupSecurityGroups:

    def test_unused_sg_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(
            mock_client,
            sgs=[_sg("sg-1", "default"), _sg("sg-2", "unused-sg")],
            servers=[_server("s1", security_groups=[{"name": "default"}])],
        )

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "security-group" in result.output
        assert "not used by any server" in result.output

    def test_default_sg_always_skipped(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(
            mock_client,
            sgs=[_sg("sg-1", "default")],
            servers=[],
        )

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output

    def test_used_sg_ok(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(
            mock_client,
            sgs=[_sg("sg-1", "default"), _sg("sg-2", "web-sg")],
            servers=[_server("s1", security_groups=[{"name": "default"}, {"name": "web-sg"}])],
        )

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Servers in ERROR
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupServers:

    def test_error_server_detected(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, servers=[_server("s1", name="broken", status="ERROR")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "server" in result.output
        assert "error state" in result.output

    def test_active_server_ok(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, servers=[_server("s1", status="ACTIVE")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "No orphaned resources found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Delete mode
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupDelete:

    def test_dry_run_by_default(self, invoke, config_dir, mock_client, sample_profile):
        """Without --delete, just reports issues."""
        save_profile("p", sample_profile)
        set_active_profile("p")

        _setup_mock(mock_client, fips=[_fip("fip-1")])

        result = invoke(["cleanup"])
        assert result.exit_code == 0
        assert "--delete" in result.output

    def test_delete_with_yes(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        deleted_ids = []
        original_delete = mock_client.delete

        def track_delete(url, **kw):
            deleted_ids.append(url)

        _setup_mock(mock_client, fips=[_fip("fip-1"), _fip("fip-2")])
        mock_client.delete = track_delete

        result = invoke(["cleanup", "--delete", "-y"])
        assert result.exit_code == 0
        assert len(deleted_ids) == 2
        assert "cleaned up" in result.output

    def test_delete_mixed_resources(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        deleted_urls = []

        def track_delete(url, **kw):
            deleted_urls.append(url)

        _setup_mock(
            mock_client,
            fips=[_fip("fip-1")],
            volumes=[_volume("v1", status="error")],
            ports=[_port("p1")],
        )
        mock_client.delete = track_delete

        result = invoke(["cleanup", "--delete", "-y"])
        assert result.exit_code == 0
        assert len(deleted_urls) == 3
        # Should have deleted FIP, volume, and port
        assert any("floatingips" in u for u in deleted_urls)
        assert any("volumes" in u for u in deleted_urls)
        assert any("ports" in u for u in deleted_urls)

    def test_delete_failure_handled(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        def failing_delete(url, **kw):
            raise Exception("Conflict")

        _setup_mock(mock_client, fips=[_fip("fip-1")])
        mock_client.delete = failing_delete

        result = invoke(["cleanup", "--delete", "-y"])
        assert result.exit_code == 0
        assert "Conflict" in result.output
        assert "0/1" in result.output

    def test_delete_partial_success(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        call_count = {"n": 0}

        def sometimes_fail(url, **kw):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("fail")

        _setup_mock(mock_client, fips=[_fip("f1"), _fip("f2"), _fip("f3")])
        mock_client.delete = sometimes_fail

        result = invoke(["cleanup", "--delete", "-y"])
        assert result.exit_code == 0
        assert "2/3" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Combined
# ══════════════════════════════════════════════════════════════════════════


class TestCleanupCombined:

    def test_multiple_issue_types(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        _setup_mock(
            mock_client,
            fips=[_fip("fip-1")],
            volumes=[_volume("v1"), _volume("v2", status="error")],
            snapshots=[_snapshot("snap-1", created_at=old_date)],
            ports=[_port("p1")],
            sgs=[_sg("sg-1", "default"), _sg("sg-2", "orphan")],
            servers=[_server("s1", status="ERROR")],
        )

        result = invoke(["cleanup", "--older-than", "30"])
        assert result.exit_code == 0
        assert "floating-ip" in result.output
        assert "volume" in result.output
        assert "snapshot" in result.output
        assert "port" in result.output
        assert "security-group" in result.output
        assert "server" in result.output


class TestCleanupHelp:

    def test_help(self, invoke):
        result = invoke(["cleanup", "--help"])
        assert result.exit_code == 0
        assert "--delete" in result.output
        assert "--older-than" in result.output
        assert "--yes" in result.output or "-y" in result.output
