"""Tests for ``orca volume`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ───────────────────────���─────────────────────────────────��──────

VOL_ID = "11112222-3333-4444-5555-666677778888"
SNAP_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _vol(vol_id=VOL_ID, name="my-vol", status="available", size=50):
    return {
        "id": vol_id, "name": name, "status": status, "size": size,
        "volume_type": "SSD", "bootable": "false",
        "encrypted": False, "multiattach": False,
        "availability_zone": "az1",
        "snapshot_id": None, "source_volid": None,
        "description": "test volume",
        "created_at": "2025-01-01", "updated_at": "2025-01-02",
        "attachments": [],
    }


def _snap(snap_id=SNAP_ID, name="my-snap", vol_id=VOL_ID):
    return {
        "id": snap_id, "name": name, "volume_id": vol_id,
        "size": 50, "status": "available",
        "description": "test snap", "created_at": "2025-01-01",
    }


def _setup_mock(mock_client):
    mock_client.volume_url = "https://cinder.example.com/v3"
    mock_client.compute_url = "https://nova.example.com/v2.1"

    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if f"volumes/{VOL_ID}" in url and "action" not in url:
            return {"volume": _vol()}
        if "volumes/detail" in url:
            return {"volumes": [_vol()]}
        if f"snapshots/{SNAP_ID}" in url:
            return {"snapshot": _snap()}
        if "snapshots/detail" in url:
            return {"snapshots": [_snap()]}
        if "servers/detail" in url:
            return {"servers": []}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        if "/volumes" in url and "action" in url:
            return {}
        if "/volumes" in url:
            return {"volume": {"id": "new-vol", "name": "new", "size": 100}}
        if "/snapshots" in url:
            return {"snapshot": {"id": "new-snap", "name": "new"}}
        if "/backups" in url and "restore" in url:
            return {"restore": {"backup_id": BKP_ID, "volume_id": VOL_ID, "volume_name": "restored"}}
        if "/backups" in url:
            return {"backup": {"id": BKP_ID, "name": "my-backup", "volume_id": VOL_ID,
                               "status": "creating", "size": 50}}
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


# ═════════════��══════════════════════════════���═════════════════════════════
#  list
# ══════════════════════════════════════════════════════════════════════════


class TestVolumeList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "list"])
        assert result.exit_code == 0
        assert "my-" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get = lambda url, **kw: {"volumes": []}

        result = invoke(["volume", "list"])
        assert result.exit_code == 0
        assert "No volumes found" in result.output


# ══════��══════════════════════════��════════════════════════════���═══════════
#  show
# ════════════════════��═════════════════════════════════════════════════════


class TestVolumeShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "show", VOL_ID])
        assert result.exit_code == 0
        assert "my-" in result.output
        assert "50 GB" in result.output


# ═══���══════════════════════════��═══════════════════════════════��═══════════
#  create
# ════���════════════���═════════════════════════════���══════════════════════════


class TestVolumeCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "create", "--name", "data-vol", "--size", "100"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        body = state["posted"]["last_body"]["volume"]
        assert body["name"] == "data-vol"
        assert body["size"] == 100

    def test_create_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "create", "--name", "boot",
                         "--size", "30", "--type", "SSD",
                         "--description", "Boot volume"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["volume"]
        assert body["volume_type"] == "SSD"


# ═════���═══════════════════════════���══════════════════════════════���═════════
#  update
# ══════════════════════════════════════════════════════════════════════════


class TestVolumeUpdate:

    def test_update(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["volume", "update", VOL_ID, "--name", "renamed"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "update", VOL_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ═════════════���══════════════════════════���═════════════════════════════════
#  extend / retype / set-bootable / set-readonly
# ═════════════════════���═══════════════════════════��════════════════════════


class TestVolumeActions:

    def test_extend(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "extend", VOL_ID, "--size", "100"])
        assert result.exit_code == 0
        assert "Extend" in result.output

    def test_retype(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "retype", VOL_ID, "--type", "NVMe"])
        assert result.exit_code == 0
        assert "Retype" in result.output

    def test_set_bootable(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "set-bootable", VOL_ID, "--bootable"])
        assert result.exit_code == 0
        assert "bootable" in result.output.lower()

    def test_set_readonly(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "set-readonly", VOL_ID, "--readonly"])
        assert result.exit_code == 0
        assert "readonly" in result.output.lower()


# ═════════════════════════════════════════════════════���════════════════════
#  delete
# ═══════════════════════════���═══════════════════════════��══════════════════


class TestVolumeDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "delete", VOL_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ═══���══════════════════════════════════════════════════════════════════════
#  snapshot-list / show / create / delete
# ══════���══════════════════════��═════════════════════════��══════════════════


class TestSnapshots:

    def test_snapshot_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "snapshot-list"])
        assert result.exit_code == 0
        assert "my-s" in result.output

    def test_snapshot_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get = lambda url, **kw: {"snapshots": []}

        result = invoke(["volume", "snapshot-list"])
        assert result.exit_code == 0
        assert "No snapshots found" in result.output

    def test_snapshot_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "snapshot-show", SNAP_ID])
        assert result.exit_code == 0
        assert "my-snap" in result.output

    def test_snapshot_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["volume", "snapshot-create", VOL_ID, "--name", "backup"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_snapshot_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["volume", "snapshot-delete", SNAP_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ═════════════════════════════════════════════���════════════════════════════
#  tree
# ════════���═════════════════════════════════════════════════════════════════


class TestVolumeTree:

    def test_tree(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["volume", "tree"])
        assert result.exit_code == 0
        assert "my-" in result.output
        assert "1 volumes" in result.output or "50 GB" in result.output


# ═════��══════════════════════════���═════════════════════════════════════════
#  Help
# ═══��══════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════
#  migrate / revert-to-snapshot / summary
# ══════════════════════════════════════════════════════════════════════════

MSG_ID = "aa111111-1111-1111-1111-111111111111"
ATT_ID = "bb222222-2222-2222-2222-222222222222"
GRP_ID = "cc333333-3333-3333-3333-333333333333"
GT_ID  = "dd444444-4444-4444-4444-444444444444"
VT_ID  = "ee555555-5555-5555-5555-555555555555"


def _setup_extended(mock_client):
    """Extended mock adding messages, attachments, groups and summary."""
    state = _setup_mock(mock_client)
    orig_get = mock_client.get

    def _get(url, **kwargs):
        if "volumes/summary" in url:
            return {"volume-summary": {"total_count": 5, "total_size": 250}}
        if f"messages/{MSG_ID}" in url:
            return {"message": {
                "id": MSG_ID, "resource_type": "VOLUME",
                "resource_uuid": VOL_ID, "event_id": "scheduler.create.start",
                "user_message": "No space left", "message_level": "ERROR",
                "created_at": "2025-01-01", "expires_at": "2025-04-01",
            }}
        if "messages" in url:
            return {"messages": [{"id": MSG_ID, "resource_type": "VOLUME",
                                   "resource_uuid": VOL_ID,
                                   "event_id": "scheduler.create.start",
                                   "user_message": "No space left",
                                   "created_at": "2025-01-01"}]}
        if f"attachments/{ATT_ID}" in url:
            return {"attachment": {
                "id": ATT_ID, "volume_id": VOL_ID,
                "instance_uuid": "srv-1", "status": "attached",
                "attach_mode": "rw", "attached_at": "2025-01-01",
            }}
        if "attachments" in url:
            return {"attachments": [{"id": ATT_ID, "volume_id": VOL_ID,
                                      "instance_uuid": "srv-1", "status": "attached",
                                      "attach_mode": "rw", "attached_at": "2025-01-01"}]}
        if f"groups/{GRP_ID}" in url and "action" not in url:
            return {"group": {
                "id": GRP_ID, "name": "my-group", "status": "available",
                "group_type": GT_ID, "volume_types": [VT_ID],
                "availability_zone": "az1", "created_at": "2025-01-01",
            }}
        if "groups/detail" in url:
            return {"groups": [{"id": GRP_ID, "name": "my-group", "status": "available",
                                 "group_type": GT_ID, "volume_types": [VT_ID],
                                 "created_at": "2025-01-01"}]}
        return orig_get(url, **kwargs)

    orig_post = mock_client.post

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        state["posted"]["last_body"] = body
        if "/groups" in url and "action" not in url:
            return {"group": {"id": GRP_ID, "name": body.get("group", {}).get("name", "grp")}}
        return orig_post(url, **kwargs)

    mock_client.get = _get
    mock_client.post = _post
    return state


class TestVolumeMigrate:

    def test_migrate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "migrate", VOL_ID, "--host", "cinder@lvm2#LVM2"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["os-migrateVolume"]
        assert body["host"] == "cinder@lvm2#LVM2"
        assert body["force_host_copy"] is False

    def test_migrate_force(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "migrate", VOL_ID, "--host", "h", "--force-host-copy"])
        assert result.exit_code == 0
        assert state["posted"]["last_body"]["os-migrateVolume"]["force_host_copy"] is True

    def test_migrate_requires_host(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        result = invoke(["volume", "migrate", VOL_ID])
        assert result.exit_code != 0


class TestVolumeRevertToSnapshot:

    def test_revert(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "revert-to-snapshot", VOL_ID, SNAP_ID])
        assert result.exit_code == 0
        assert state["posted"]["last_body"]["revert"]["snapshot_id"] == SNAP_ID


class TestVolumeSummary:

    def test_summary(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "summary"])
        assert result.exit_code == 0
        assert "5" in result.output
        assert "250" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  messages
# ══════════════════════════════════════════════════════════════════════════


class TestVolumeMessages:

    def test_message_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "message-list"])
        assert result.exit_code == 0
        assert "VOLU" in result.output or "No space" in result.output

    def test_message_list_filter_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "message-list", "--resource-type", "VOLUME"])
        assert result.exit_code == 0

    def test_message_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "message-show", MSG_ID])
        assert result.exit_code == 0
        assert "No space left" in result.output

    def test_message_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_extended(mock_client)
        result = invoke(["volume", "message-delete", MSG_ID, "--yes"])
        assert result.exit_code == 0
        assert any(MSG_ID in u for u in state["deleted"])

    def test_invalid_resource_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        result = invoke(["volume", "message-list", "--resource-type", "INVALID"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  attachments
# ══════════════════════════════════════════════════════════════════════════


class TestVolumeAttachments:

    def test_attachment_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "attachment-list"])
        assert result.exit_code == 0
        assert "att" in result.output.lower() or "attached" in result.output

    def test_attachment_list_filter(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "attachment-list", "--volume-id", VOL_ID])
        assert result.exit_code == 0

    def test_attachment_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "attachment-show", ATT_ID])
        assert result.exit_code == 0
        assert "attached" in result.output

    def test_attachment_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_extended(mock_client)
        result = invoke(["volume", "attachment-delete", ATT_ID, "--yes"])
        assert result.exit_code == 0
        assert any(ATT_ID in u for u in state["deleted"])


# ══════════════════════════════════════════════════════════════════════════
#  groups
# ══════════════════════════════════════════════════════════════════════════


class TestVolumeGroups:

    def test_group_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "group-list"])
        assert result.exit_code == 0
        assert "my-" in result.output

    def test_group_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_extended(mock_client)
        result = invoke(["volume", "group-show", GRP_ID])
        assert result.exit_code == 0
        assert "my-group" in result.output

    def test_group_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_extended(mock_client)
        result = invoke(["volume", "group-create", "my-group",
                         "--group-type", GT_ID, "--volume-type", VT_ID])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["group"]
        assert body["group_type"] == GT_ID
        assert VT_ID in body["volume_types"]

    def test_group_create_requires_group_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        result = invoke(["volume", "group-create", "grp", "--volume-type", VT_ID])
        assert result.exit_code != 0

    def test_group_update_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "group-update", GRP_ID, "--name", "new-name"])
        assert result.exit_code == 0
        assert state["put_data"]["last_body"]["group"]["name"] == "new-name"

    def test_group_update_add_remove_volumes(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "group-update", GRP_ID,
                         "--add-volume", VOL_ID, "--remove-volume", SNAP_ID])
        assert result.exit_code == 0
        body = state["put_data"]["last_body"]["group"]
        assert VOL_ID in body["add_volumes"]
        assert SNAP_ID in body["remove_volumes"]

    def test_group_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)
        result = invoke(["volume", "group-update", GRP_ID])
        assert result.exit_code == 0
        assert "Nothing to update" in result.output

    def test_group_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "group-delete", GRP_ID, "--yes"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["delete"]
        assert body["delete-volumes"] is False

    def test_group_delete_with_volumes(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)
        result = invoke(["volume", "group-delete", GRP_ID, "--delete-volumes", "--yes"])
        assert result.exit_code == 0
        assert state["posted"]["last_body"]["delete"]["delete-volumes"] is True


# ══════════════════════════════════════════════════════════════════════════
#  backup-create / backup-restore
# ══════════════════════════════════════════════════════════════════════════

BKP_ID = "ff001122-3344-5566-7788-99aabbccddee"


class TestVolumeBackupCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "backup-create", VOL_ID, "--name", "my-backup"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["backup"]
        assert body["volume_id"] == VOL_ID
        assert body["name"] == "my-backup"

    def test_create_incremental_force(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "backup-create", VOL_ID,
                         "--incremental", "--force"])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["backup"]
        assert body["incremental"] is True
        assert body["force"] is True

    def test_create_with_snapshot(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "backup-create", VOL_ID, "--snapshot-id", SNAP_ID])
        assert result.exit_code == 0
        assert state["posted"]["last_body"]["backup"]["snapshot_id"] == SNAP_ID


class TestVolumeBackupRestore:

    def test_restore(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["volume", "backup-restore", BKP_ID])
        assert result.exit_code == 0
        assert "restore" in result.output.lower() or "backup" in result.output.lower()

    def test_restore_to_volume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "backup-restore", BKP_ID, "--volume-id", VOL_ID])
        assert result.exit_code == 0
        body = state["posted"]["last_body"]["restore"]
        assert body["volume_id"] == VOL_ID

    def test_restore_with_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["volume", "backup-restore", BKP_ID, "--name", "restored-vol"])
        assert result.exit_code == 0
        assert state["posted"]["last_body"]["restore"]["name"] == "restored-vol"


class TestVolumeHelp:

    def test_volume_help(self, invoke):
        result = invoke(["volume", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "update", "delete",
                    "extend", "retype", "set-bootable", "set-readonly",
                    "snapshot-list", "snapshot-show", "snapshot-create",
                    "snapshot-delete", "tree",
                    "migrate", "revert-to-snapshot", "summary",
                    "message-list", "message-show", "message-delete",
                    "attachment-list", "attachment-show", "attachment-delete",
                    "group-list", "group-show", "group-create",
                    "group-update", "group-delete",
                    "backup-list", "backup-show", "backup-create",
                    "backup-delete", "backup-restore"):
            assert cmd in result.output
