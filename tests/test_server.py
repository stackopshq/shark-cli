"""Tests for ``orca server`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

SRV_ID = "11112222-3333-4444-5555-666677778888"
SRV_ID_B = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
VOL_ID = "22223333-4444-5555-6666-777788889999"
PORT_ID = "33334444-5555-6666-7777-888899990000"
NET_ID = "44445555-6666-7777-8888-999900001111"
IMG_ID = "55556666-7777-8888-9999-000011112222"


def _srv(srv_id=SRV_ID, name="web-1", status="ACTIVE"):
    return {
        "id": srv_id, "name": name, "status": status,
        "flavor": {"id": "flav-1", "original_name": "m1.small"},
        "image": {"id": IMG_ID},
        "addresses": {"my-net": [
            {"addr": "10.0.0.5", "OS-EXT-IPS:type": "fixed"},
            {"addr": "203.0.113.10", "OS-EXT-IPS:type": "floating"},
        ]},
        "key_name": "my-key",
        "security_groups": [{"name": "default"}],
        "config_drive": "", "created": "2025-01-01", "updated": "2025-01-02",
        "OS-EXT-STS:power_state": 1,
        "OS-EXT-STS:task_state": None,
        "OS-EXT-STS:vm_state": "active",
        "OS-EXT-AZ:availability_zone": "az1",
        "tenant_id": "proj-1", "user_id": "user-1", "hostId": "host-1",
        "metadata": {},
        "os-extended-volumes:volumes_attached": [{"id": VOL_ID}],
    }


def _setup_mock(mock_client):
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.volume_url = "https://cinder.example.com/v3"

    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if f"servers/{SRV_ID}/os-volume_attachments" in url:
            return {"volumeAttachments": [
                {"id": "att-1", "volumeId": VOL_ID, "device": "/dev/vda"},
            ]}
        if f"servers/{SRV_ID}/os-interface" in url:
            return {"interfaceAttachments": [
                {"port_id": PORT_ID, "net_id": NET_ID,
                 "fixed_ips": [{"ip_address": "10.0.0.5"}],
                 "mac_addr": "fa:16:3e:aa:bb:cc", "port_state": "ACTIVE"},
            ]}
        if f"servers/{SRV_ID}/os-server-password" in url:
            return {"password": ""}
        if f"servers/{SRV_ID}" in url:
            return {"server": _srv()}
        if f"servers/{SRV_ID_B}" in url:
            return {"server": _srv(SRV_ID_B, "web-2", "SHUTOFF")}
        if "servers/detail" in url:
            return {"servers": [_srv(), _srv(SRV_ID_B, "web-2", "SHUTOFF")]}
        if f"volumes/{VOL_ID}" in url:
            return {"volume": {"size": 20, "volume_image_metadata": {"image_id": IMG_ID}}}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_url"] = url
        posted["last_body"] = body
        if "remote-consoles" in url:
            return {"remote_console": {"url": "https://vnc.example.com/token"}}
        if "/servers" in url and "action" not in url and "remote-consoles" not in url:
            return {"server": {"id": "new-srv", "name": "new", "adminPass": "secret"}}
        if "/action" in url:
            if "os-getConsoleOutput" in body:
                return {"output": "Boot log line 1\nBoot log line 2"}
            if "remote_console" in body:
                return {"remote_console": {"url": "https://vnc.example.com/token"}}
            if "rebuild" in body:
                return {"server": {"id": SRV_ID, "adminPass": "newpass"}}
            if "rescue" in body:
                return {"adminPass": "rescuepass"}
            if "createImage" in body:
                return {}
            return {}
        if "/snapshots" in url:
            return {"snapshot": {"id": "snap-1"}}
        if "/os-volume_attachments" in url:
            return {"volumeAttachment": {"device": "/dev/vdb", "volumeId": VOL_ID}}
        if "/os-interface" in url:
            return {"interfaceAttachment": {"port_id": "new-port", "fixed_ips": [{"ip_address": "10.0.0.99"}]}}
        return {}

    def _put(url, **kwargs):
        body = kwargs.get("json", {})
        put_data["last_body"] = body

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_data": put_data, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  list
# ══════════════════════════════════════════════════════════════════════════


class TestServerList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "list"])
        assert result.exit_code == 0
        assert "web-" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.get = lambda url, **kw: {"servers": []}

        result = invoke(["server", "list"])
        assert result.exit_code == 0
        assert "No servers found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  show
# ══════════════════════════════════════════════════════════════════════════


class TestServerShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "show", SRV_ID])
        assert result.exit_code == 0
        assert "web-1" in result.output
        assert "ACTIVE" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════════════════════


class TestServerCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "create",
                         "--name", "my-vm",
                         "--flavor", "flav-1",
                         "--image", IMG_ID,
                         "--disk-size", "30"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        body = state["posted"]["last_body"]["server"]
        assert body["name"] == "my-vm"
        assert body["flavorRef"] == "flav-1"

    def test_create_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "create",
                         "--name", "my-vm",
                         "--flavor", "flav-1",
                         "--image", IMG_ID,
                         "--network", NET_ID,
                         "--key-name", "my-key",
                         "--security-group", "default"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["server"]
        assert body["networks"] == [{"uuid": NET_ID}]
        assert body["key_name"] == "my-key"


# ══════════════════════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════════════════════


class TestServerDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "delete", SRV_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  Actions: start, stop, reboot, pause, unpause, suspend, resume, etc.
# ══════════════════════════════════════════════════════════════════════════


class TestServerActions:

    def test_start(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "start", SRV_ID])
        assert result.exit_code == 0
        assert "Start" in result.output

    def test_stop(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "stop", SRV_ID])
        assert result.exit_code == 0
        assert "Stop" in result.output

    def test_reboot_soft(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "reboot", SRV_ID])
        assert result.exit_code == 0
        assert "SOFT" in result.output

    def test_reboot_hard(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "reboot", SRV_ID, "--hard"])
        assert result.exit_code == 0
        assert "HARD" in result.output

    def test_pause(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "pause", SRV_ID])
        assert result.exit_code == 0
        assert "Pause" in result.output

    def test_unpause(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "unpause", SRV_ID])
        assert result.exit_code == 0
        assert "Unpause" in result.output

    def test_suspend(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "suspend", SRV_ID])
        assert result.exit_code == 0
        assert "Suspend" in result.output

    def test_resume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "resume", SRV_ID])
        assert result.exit_code == 0
        assert "Resume" in result.output

    def test_lock(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "lock", SRV_ID])
        assert result.exit_code == 0
        assert "Lock" in result.output

    def test_unlock(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "unlock", SRV_ID])
        assert result.exit_code == 0
        assert "Unlock" in result.output

    def test_shelve(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "shelve", SRV_ID])
        assert result.exit_code == 0
        assert "Shelve" in result.output

    def test_unshelve(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "unshelve", SRV_ID])
        assert result.exit_code == 0
        assert "Unshelve" in result.output

    def test_rescue(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "rescue", SRV_ID])
        assert result.exit_code == 0
        assert "Rescue" in result.output or "rescue" in result.output.lower()

    def test_unrescue(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "unrescue", SRV_ID])
        assert result.exit_code == 0
        assert "Unrescue" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  resize / confirm / revert
# ══════════════════════════════════════════════════════════════════════════


class TestServerResize:

    def test_resize(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "resize", SRV_ID, "--flavor", "m1.large"])
        assert result.exit_code == 0
        assert "Resize" in result.output

    def test_confirm_resize(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "confirm-resize", SRV_ID])
        assert result.exit_code == 0
        assert "Confirm" in result.output

    def test_revert_resize(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "revert-resize", SRV_ID])
        assert result.exit_code == 0
        assert "Revert" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  rebuild
# ══════════════════════════════════════════════════════════════════════════


class TestServerRebuild:

    def test_rebuild(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "rebuild", SRV_ID, "--image", IMG_ID, "-y"])
        assert result.exit_code == 0
        assert "Rebuild" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  rename
# ══════════════════════════════════════════════════════════════════════════


class TestServerRename:

    def test_rename(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "rename", SRV_ID, "new-name"])
        assert result.exit_code == 0
        assert "renamed" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  create-image
# ══════════════════════════════════════════════════════════════════════════


class TestServerCreateImage:

    def test_create_image(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "create-image", SRV_ID, "my-snapshot"])
        assert result.exit_code == 0
        assert "my-snapshot" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Volume attachments
# ══════════════════════════════════════════════════════════════════════════


class TestServerVolumes:

    def test_attach_volume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "attach-volume", SRV_ID, VOL_ID])
        assert result.exit_code == 0
        assert "attached" in result.output.lower()

    def test_detach_volume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "detach-volume", SRV_ID, VOL_ID])
        assert result.exit_code == 0
        assert "detached" in result.output.lower()

    def test_list_volumes(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "list-volumes", SRV_ID])
        assert result.exit_code == 0
        assert "/dev/vda" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Interface attachments
# ══════════════════════════════════════════════════════════════════════════


class TestServerInterfaces:

    def test_attach_interface(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "attach-interface", SRV_ID, "--net-id", NET_ID])
        assert result.exit_code == 0
        assert "attached" in result.output.lower()

    def test_attach_interface_no_args(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "attach-interface", SRV_ID])
        assert result.exit_code != 0

    def test_detach_interface(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["server", "detach-interface", SRV_ID, PORT_ID])
        assert result.exit_code == 0
        assert "detached" in result.output.lower()

    def test_list_interfaces(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "list-interfaces", SRV_ID])
        assert result.exit_code == 0
        assert "10.0" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  console-log
# ══════════════════════════════════════════════════════════════════════════


class TestServerConsoleLog:

    def test_console_log(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "console-log", SRV_ID])
        assert result.exit_code == 0
        assert "Boot log" in result.output

    def test_console_log_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.compute_url = "https://nova.example.com/v2.1"
        mock_client.post = lambda url, **kw: {"output": ""}

        result = invoke(["server", "console-log", SRV_ID])
        assert result.exit_code == 0
        assert "No console output" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  console-url
# ══════════════════════════════════════════════════════════════════════════


class TestServerConsoleUrl:

    def test_console_url(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "console-url", SRV_ID])
        assert result.exit_code == 0
        assert "vnc.example.com" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  snapshot (server + volumes)
# ══════════════════════════════════════════════════════════════════════════


class TestServerSnapshot:

    def test_snapshot(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "snapshot", SRV_ID])
        assert result.exit_code == 0
        assert "web-1-image" in result.output
        assert "Snapshot complete" in result.output

    def test_snapshot_custom_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "snapshot", SRV_ID, "--name", "backup"])
        assert result.exit_code == 0
        assert "backup-image" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  diff
# ══════════════════════════════════════════════════════════════════════════


class TestServerDiff:

    def test_diff(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "diff", SRV_ID, SRV_ID_B])
        assert result.exit_code == 0
        assert "web-1" in result.output
        assert "web-2" in result.output
        assert "difference" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  bulk
# ══════════════════════════════════════════════════════════════════════════


class TestServerBulk:

    def test_bulk_stop(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "bulk", "stop", "--name", "web-*", "-y"])
        assert result.exit_code == 0
        assert "2/2" in result.output

    def test_bulk_no_filter(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "bulk", "stop"])
        assert result.exit_code != 0

    def test_bulk_no_match(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "bulk", "stop", "--name", "nonexistent-*", "-y"])
        assert result.exit_code == 0
        assert "No servers match" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  clone
# ══════════════════════════════════════════════════════════════════════════


class TestServerClone:

    def test_clone(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["server", "clone", SRV_ID, "--name", "web-clone"])
        assert result.exit_code == 0
        assert "web-clone" in result.output
        assert "creation started" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════
#  evacuate / dump-create / restore
# ══════════════════════════════════════════════════════════════════════════


class TestServerEvacuate:

    def test_evacuate_basic(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "evacuate", SRV_ID])
        assert result.exit_code == 0
        assert "evacuate" in state["posted"]["last_body"]
        assert "evacuation started" in result.output

    def test_evacuate_with_host(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "evacuate", SRV_ID, "--host", "compute02"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["evacuate"]
        assert body["host"] == "compute02"

    def test_evacuate_shared_storage(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "evacuate", SRV_ID, "--on-shared-storage"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["evacuate"]
        assert body["onSharedStorage"] is True


class TestServerDumpCreate:

    def test_dump_create(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "dump-create", SRV_ID])
        assert result.exit_code == 0
        assert "trigger_crash_dump" in state["posted"]["last_body"]
        assert "triggered" in result.output

    def test_dump_create_help(self, invoke):
        result = invoke(["server", "dump-create", "--help"])
        assert result.exit_code == 0


class TestServerRestore:

    def test_restore(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "restore", SRV_ID])
        assert result.exit_code == 0
        assert "restore" in state["posted"]["last_body"]
        assert "restored" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  fixed-ip add/remove
# ══════════════════════════════════════════════════════════════════════════


class TestServerFixedIP:

    def test_add_fixed_ip(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "add-fixed-ip", SRV_ID, NET_ID])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]
        assert "addFixedIp" in body
        assert body["addFixedIp"]["networkId"] == NET_ID

    def test_remove_fixed_ip(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "remove-fixed-ip", SRV_ID, "10.0.0.5"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]
        assert "removeFixedIp" in body
        assert body["removeFixedIp"]["address"] == "10.0.0.5"


# ══════════════════════════════════════════════════════════════════════════
#  port / network add/remove
# ══════════════════════════════════════════════════════════════════════════


class TestServerPortNetwork:

    def test_add_port(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "add-port", SRV_ID, PORT_ID])
        assert result.exit_code == 0
        assert "attached" in result.output or "port" in result.output.lower()
        body = state["posted"]["last_body"]
        assert body["interfaceAttachment"]["port_id"] == PORT_ID

    def test_remove_port(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "remove-port", SRV_ID, PORT_ID])
        assert result.exit_code == 0
        assert any(PORT_ID in u for u in state["deleted"])

    def test_add_network(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "add-network", SRV_ID, NET_ID])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]
        assert body["interfaceAttachment"]["net_id"] == NET_ID

    def test_remove_network_found(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "remove-network", SRV_ID, NET_ID])
        assert result.exit_code == 0
        # Should delete the interface with matching net_id
        assert any("os-interface" in u for u in state["deleted"])
        assert "removed" in result.output

    def test_remove_network_not_found(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "remove-network", SRV_ID, "no-such-net"])
        assert result.exit_code == 0
        assert "No interfaces found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  unset
# ══════════════════════════════════════════════════════════════════════════


class TestServerUnset:

    def test_unset_property(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "unset", SRV_ID, "--property", "env"])
        assert result.exit_code == 0
        assert any("metadata/env" in u for u in state["deleted"])
        assert "updated" in result.output

    def test_unset_multiple_properties(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "unset", SRV_ID,
                         "--property", "env", "--property", "team"])
        assert result.exit_code == 0
        assert any("metadata/env" in u for u in state["deleted"])
        assert any("metadata/team" in u for u in state["deleted"])

    def test_unset_tag(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "unset", SRV_ID, "--tag", "web"])
        assert result.exit_code == 0
        assert any("tags/web" in u for u in state["deleted"])

    def test_unset_nothing(self, invoke, mock_client):
        _setup_mock(mock_client)
        result = invoke(["server", "unset", SRV_ID])
        assert result.exit_code == 0
        assert "Nothing to unset" in result.output

    def test_unset_mixed(self, invoke, mock_client):
        state = _setup_mock(mock_client)
        result = invoke(["server", "unset", SRV_ID,
                         "--property", "env", "--tag", "frontend"])
        assert result.exit_code == 0
        assert any("metadata/env" in u for u in state["deleted"])
        assert any("tags/frontend" in u for u in state["deleted"])


# ══════════════════════════════════════════════════════════════════════════
#  help
# ══════════════════════════════════════════════════════════════════════════


class TestServerHelp:

    def test_server_help(self, invoke):
        result = invoke(["server", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "start", "stop",
                    "reboot", "pause", "unpause", "suspend", "resume",
                    "lock", "unlock", "rescue", "unrescue",
                    "shelve", "unshelve", "resize", "rebuild", "rename",
                    "create-image", "attach-volume", "detach-volume",
                    "list-volumes", "attach-interface", "detach-interface",
                    "list-interfaces", "console-log", "console-url",
                    "snapshot", "wait", "bulk", "clone", "diff",
                    "ssh", "port-forward", "password",
                    "evacuate", "dump-create", "restore",
                    "add-fixed-ip", "remove-fixed-ip",
                    "add-port", "remove-port",
                    "add-network", "remove-network",
                    "unset"):
            assert cmd in result.output
