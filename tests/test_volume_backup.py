"""Tests for `orca volume backup-*` (Cinder native backup)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# Valid UUIDs for validate_id
VOL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BKP_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
RST_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


# ══════════════════════════════════════════════════════════════════════════
#  backup-list
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupList:

    def test_list(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get.return_value = {
            "backups": [
                {"id": BKP_ID, "name": "my-backup", "volume_id": VOL_ID,
                 "status": "available", "size": 50, "is_incremental": False,
                 "created_at": "2024-01-01T00:00:00Z"},
            ]
        }
        result = invoke(["volume", "backup-list"])
        assert result.exit_code == 0
        assert "my-" in result.output  # Rich truncates in narrow CliRunner terminal

    def test_list_empty(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get.return_value = {"backups": []}
        result = invoke(["volume", "backup-list"])
        assert result.exit_code == 0
        assert "No backups" in result.output

    def test_list_all_projects(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get.return_value = {"backups": []}
        result = invoke(["volume", "backup-list", "--all-projects"])
        assert result.exit_code == 0
        call_kwargs = mock_client.get.call_args[1]
        assert call_kwargs.get("params", {}).get("all_tenants") == 1


# ══════════════════════════════════════════════════════════════════════════
#  backup-show
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupShow:

    def test_show(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.get.return_value = {
            "backup": {
                "id": BKP_ID, "name": "my-backup", "volume_id": VOL_ID,
                "snapshot_id": None, "status": "available", "size": 50,
                "is_incremental": True, "has_dependent_backups": False,
                "container": "backups", "availability_zone": "nova",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T01:00:00Z",
                "description": "daily backup",
            }
        }
        result = invoke(["volume", "backup-show", BKP_ID])
        assert result.exit_code == 0
        assert "my-backup" in result.output
        assert "available" in result.output
        assert "yes" in result.output  # is_incremental


# ══════════════════════════════════════════════════════════════════════════
#  backup-create
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupCreate:

    _FULL_BKP = {
        "backup": {
            "id": BKP_ID, "name": "my-backup", "volume_id": VOL_ID,
            "snapshot_id": None, "container": None, "description": None,
            "status": "available", "size": 10, "created_at": "2024-01-01T00:00:00Z",
        }
    }

    def test_create_basic(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"backup": {"id": BKP_ID, "name": "my-backup"}}
        mock_client.get.return_value = self._FULL_BKP
        result = invoke(["volume", "backup-create", VOL_ID, "--name", "my-backup"])
        assert result.exit_code == 0
        assert BKP_ID in result.output
        body = mock_client.post.call_args[1]["json"]["backup"]
        assert body["volume_id"] == VOL_ID
        assert body["name"] == "my-backup"

    def test_create_incremental(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"backup": {"id": BKP_ID, "name": None}}
        mock_client.get.return_value = self._FULL_BKP
        result = invoke(["volume", "backup-create", VOL_ID, "--incremental"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["backup"]
        assert body.get("incremental") is True

    def test_create_force(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"backup": {"id": BKP_ID, "name": None}}
        mock_client.get.return_value = self._FULL_BKP
        result = invoke(["volume", "backup-create", VOL_ID, "--force"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["backup"]
        assert body.get("force") is True

    def test_create_with_wait(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"backup": {"id": BKP_ID, "name": "bk"}}
        mock_client.get.return_value = self._FULL_BKP
        with patch("orca_cli.commands.volume.wait_for_resource") as mock_wait:
            result = invoke(["volume", "backup-create", VOL_ID, "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        _, kwargs = mock_wait.call_args
        assert kwargs.get("target_status") == "available"


# ══════════════════════════════════════════════════════════════════════════
#  backup-delete
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupDelete:

    def test_delete(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        result = invoke(["volume", "backup-delete", BKP_ID, "--yes"])
        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_client.delete.assert_called_once()

    def test_delete_force(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        result = invoke(["volume", "backup-delete", BKP_ID, "--yes", "--force"])
        assert result.exit_code == 0
        _, kwargs = mock_client.delete.call_args
        assert kwargs.get("params", {}).get("force") is True


# ══════════════════════════════════════════════════════════════════════════
#  backup-restore
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupRestore:

    def test_restore_new_volume(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"restore": {"volume_id": RST_ID}}
        result = invoke(["volume", "backup-restore", BKP_ID])
        assert result.exit_code == 0
        assert RST_ID in result.output

    def test_restore_to_existing_volume(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"restore": {"volume_id": VOL_ID}}
        result = invoke(["volume", "backup-restore", BKP_ID, "--volume-id", VOL_ID])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["restore"]
        assert body["volume_id"] == VOL_ID

    def test_restore_with_wait(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"restore": {"volume_id": RST_ID}}
        with patch("orca_cli.commands.volume.wait_for_resource") as mock_wait:
            result = invoke(["volume", "backup-restore", BKP_ID, "--wait"])
        assert result.exit_code == 0
        mock_wait.assert_called_once()
        assert "available" in str(mock_wait.call_args)

    def test_restore_with_name(self, invoke, mock_client):
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.post.return_value = {"restore": {"volume_id": RST_ID}}
        result = invoke(["volume", "backup-restore", BKP_ID, "--name", "restored"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["restore"]
        assert body["name"] == "restored"


# ══════════════════════════════════════════════════════════════════════════
#  --help checks
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeBackupHelp:

    @pytest.mark.parametrize("sub", [
        "backup-list", "backup-show", "backup-create", "backup-delete", "backup-restore"
    ])
    def test_help(self, invoke, sub):
        result = invoke(["volume", sub, "--help"])
        assert result.exit_code == 0
