"""Tests for Cinder admin commands: volume types, transfers, QoS, services, set/unset."""

from __future__ import annotations

import pytest

VOL  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SNAP = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
TYPE = "cccccccc-cccc-cccc-cccc-cccccccccccc"
QOS  = "dddddddd-dddd-dddd-dddd-dddddddddddd"
XFER = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
PRJ  = "ffffffff-ffff-ffff-ffff-ffffffffffff"
CINDER = "https://cinder.example.com/v3/project"


def _vol(mock_client):
    mock_client.volume_url = CINDER
    return mock_client


# ══════════════════════════════════════════════════════════════════════════
#  volume set / unset (metadata)
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeSet:

    def test_set_name(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "set", VOL, "--name", "new-name"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["volume"]
        assert body["name"] == "new-name"

    def test_set_property(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "set", VOL, "--property", "env=prod"])
        assert result.exit_code == 0
        mock_client.post.assert_called_once()
        body = mock_client.post.call_args[1]["json"]["metadata"]
        assert body["env"] == "prod"

    def test_set_nothing(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "set", VOL])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()
        mock_client.post.assert_not_called()

    def test_set_invalid_property(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "set", VOL, "--property", "bad-format"])
        assert result.exit_code != 0

    def test_help(self, invoke):
        assert invoke(["volume", "set", "--help"]).exit_code == 0


class TestVolumeUnset:

    def test_unset(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "unset", VOL, "--property", "env"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        url = mock_client.delete.call_args[0][0]
        assert f"/volumes/{VOL}/metadata/env" in url

    def test_unset_multiple(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "unset", VOL, "--property", "a", "--property", "b"])
        assert mock_client.delete.call_count == 2

    def test_unset_nothing(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "unset", VOL])
        assert result.exit_code == 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "unset", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  volume snapshot-set
# ══════════════════════════════════════════════════════════════════════════

class TestSnapshotSet:

    def test_set_name(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "snapshot-set", SNAP, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["snapshot"]
        assert body["name"] == "renamed"

    def test_set_property(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "snapshot-set", SNAP, "--property", "key=val"])
        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    def test_set_nothing(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "snapshot-set", SNAP])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "snapshot-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  volume type-list / show / create / set / delete
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeTypeList:

    def _type(self, **kw):
        return {"id": TYPE, "name": "ssd", "is_public": True, "description": "", **kw}

    def test_list(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"volume_types": [self._type()]}
        result = invoke(["volume", "type-list"])
        assert result.exit_code == 0
        assert "ssd" in result.output

    def test_list_default(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"volume_type": self._type()}
        result = invoke(["volume", "type-list", "--default"])
        assert result.exit_code == 0
        url = mock_client.get.call_args[0][0]
        assert "/types/default" in url

    def test_list_empty(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"volume_types": []}
        result = invoke(["volume", "type-list"])
        assert "No volume types" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "type-list", "--help"]).exit_code == 0


class TestVolumeTypeShow:

    def test_show(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"volume_type": {
            "id": TYPE, "name": "ssd", "is_public": True,
            "description": "Fast SSD", "extra_specs": {"volume_backend_name": "lvm-ssd"},
        }}
        result = invoke(["volume", "type-show", TYPE])
        assert result.exit_code == 0
        assert "ssd" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "type-show", "--help"]).exit_code == 0


class TestVolumeTypeCreate:

    def test_create(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"volume_type": {"id": TYPE, "name": "ssd"}}
        result = invoke(["volume", "type-create", "ssd"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["volume_type"]
        assert body["name"] == "ssd"

    def test_create_with_specs(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"volume_type": {"id": TYPE, "name": "ssd"}}
        invoke(["volume", "type-create", "ssd",
                "--property", "volume_backend_name=lvm"])
        assert mock_client.post.call_count == 2  # type + extra_specs

    def test_help(self, invoke):
        assert invoke(["volume", "type-create", "--help"]).exit_code == 0


class TestVolumeTypeSet:

    def test_set_name(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-set", TYPE, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["volume_type"]
        assert body["name"] == "renamed"

    def test_set_nothing(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-set", TYPE])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "type-set", "--help"]).exit_code == 0


class TestVolumeTypeDelete:

    def test_delete_yes(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-delete", TYPE, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-delete", TYPE], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "type-delete", "--help"]).exit_code == 0


class TestVolumeTypeAccess:

    def test_access_list(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"volume_type_access": [
            {"volume_type_id": TYPE, "project_id": PRJ}
        ]}
        result = invoke(["volume", "type-access-list", TYPE])
        assert result.exit_code == 0

    def test_access_add(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-access-add", TYPE, PRJ])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["addProjectAccess"]["project"] == PRJ

    def test_access_remove_yes(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-access-remove", TYPE, PRJ, "--yes"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["removeProjectAccess"]["project"] == PRJ

    def test_access_remove_requires_confirm(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "type-access-remove", TYPE, PRJ], input="n\n")
        assert result.exit_code != 0

    def test_help_access_list(self, invoke):
        assert invoke(["volume", "type-access-list", "--help"]).exit_code == 0

    def test_help_access_add(self, invoke):
        assert invoke(["volume", "type-access-add", "--help"]).exit_code == 0

    def test_help_access_remove(self, invoke):
        assert invoke(["volume", "type-access-remove", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  volume transfer-*
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeTransferCreate:

    def test_create(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"transfer": {
            "id": XFER, "volume_id": VOL, "auth_key": "secret123"
        }}
        result = invoke(["volume", "transfer-create", VOL, "--name", "my-transfer"])
        assert result.exit_code == 0
        assert "secret" in result.output
        body = mock_client.post.call_args[1]["json"]["transfer"]
        assert body["volume_id"] == VOL
        assert body["name"] == "my-transfer"

    def test_calls_correct_url(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"transfer": {"id": XFER, "auth_key": "x"}}
        invoke(["volume", "transfer-create", VOL])
        url = mock_client.post.call_args[0][0]
        assert "/volume-transfers" in url

    def test_help(self, invoke):
        assert invoke(["volume", "transfer-create", "--help"]).exit_code == 0


class TestVolumeTransferList:

    def test_list(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"transfers": [
            {"id": XFER, "name": "my-transfer", "volume_id": VOL, "created_at": "2026-01-01"}
        ]}
        result = invoke(["volume", "transfer-list"])
        assert result.exit_code == 0

    def test_list_all_projects(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"transfers": []}
        invoke(["volume", "transfer-list", "--all-projects"])
        assert mock_client.get.call_args[1]["params"].get("all_tenants") == 1

    def test_list_empty(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"transfers": []}
        result = invoke(["volume", "transfer-list"])
        assert "No transfers" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "transfer-list", "--help"]).exit_code == 0


class TestVolumeTransferShow:

    def test_show(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"transfer": {
            "id": XFER, "name": "t", "volume_id": VOL, "created_at": "2026-01-01"
        }}
        result = invoke(["volume", "transfer-show", XFER])
        assert result.exit_code == 0

    def test_help(self, invoke):
        assert invoke(["volume", "transfer-show", "--help"]).exit_code == 0


class TestVolumeTransferAccept:

    def test_accept(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "transfer-accept", XFER, "myauthkey"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["accept"]
        assert body["auth_key"] == "myauthkey"

    def test_calls_correct_url(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "transfer-accept", XFER, "key"])
        url = mock_client.post.call_args[0][0]
        assert f"/volume-transfers/{XFER}/accept" in url

    def test_help(self, invoke):
        assert invoke(["volume", "transfer-accept", "--help"]).exit_code == 0


class TestVolumeTransferDelete:

    def test_delete_yes(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "transfer-delete", XFER, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "transfer-delete", XFER], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "transfer-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  volume qos-*
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeQosList:

    def test_list(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"qos_specs": [
            {"id": QOS, "name": "high-iops", "consumer": "back-end", "specs": {}}
        ]}
        result = invoke(["volume", "qos-list"])
        assert result.exit_code == 0
        assert "high-iops" in result.output

    def test_list_empty(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"qos_specs": []}
        result = invoke(["volume", "qos-list"])
        assert "No QoS" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "qos-list", "--help"]).exit_code == 0


class TestVolumeQosShow:

    def test_show(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"qos_specs": {
            "id": QOS, "name": "high-iops", "consumer": "back-end",
            "specs": {"total_iops_sec": "1000"},
        }}
        result = invoke(["volume", "qos-show", QOS])
        assert result.exit_code == 0
        assert "high-iops" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "qos-show", "--help"]).exit_code == 0


class TestVolumeQosCreate:

    def test_create(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"qos_specs": {"id": QOS}}
        result = invoke(["volume", "qos-create", "high-iops",
                         "--consumer", "back-end",
                         "--property", "total_iops_sec=1000"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]["qos_specs"]
        assert body["name"] == "high-iops"
        assert body["specs"]["total_iops_sec"] == "1000"

    def test_create_no_specs(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.post.return_value = {"qos_specs": {"id": QOS}}
        result = invoke(["volume", "qos-create", "basic"])
        assert result.exit_code == 0

    def test_help(self, invoke):
        assert invoke(["volume", "qos-create", "--help"]).exit_code == 0


class TestVolumeQosSet:

    def test_set(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-set", QOS, "--property", "total_iops_sec=2000"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]["qos_specs"]["specs"]
        assert body["total_iops_sec"] == "2000"

    def test_set_nothing(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-set", QOS])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "qos-set", "--help"]).exit_code == 0


class TestVolumeQosDelete:

    def test_delete_yes(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-delete", QOS, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_force(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "qos-delete", QOS, "--yes", "--force"])
        assert mock_client.delete.call_args[1].get("params") == {"force": True}

    def test_delete_requires_confirm(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-delete", QOS], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["volume", "qos-delete", "--help"]).exit_code == 0


class TestVolumeQosAssociate:

    def test_associate(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-associate", QOS, TYPE])
        assert result.exit_code == 0
        assert mock_client.get.call_args[1]["params"]["vol_type_id"] == TYPE

    def test_calls_correct_url(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "qos-associate", QOS, TYPE])
        url = mock_client.get.call_args[0][0]
        assert f"/qos-specs/{QOS}/associate" in url

    def test_help(self, invoke):
        assert invoke(["volume", "qos-associate", "--help"]).exit_code == 0


class TestVolumeQosDisassociate:

    def test_disassociate(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "qos-disassociate", QOS, TYPE])
        assert result.exit_code == 0

    def test_disassociate_all(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "qos-disassociate", QOS, TYPE, "--all"])
        url = mock_client.get.call_args[0][0]
        assert "disassociate_all" in url

    def test_help(self, invoke):
        assert invoke(["volume", "qos-disassociate", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  volume service-list / service-set
# ══════════════════════════════════════════════════════════════════════════

class TestVolumeServiceList:

    def _svc(self, **kw):
        return {"binary": "cinder-volume", "host": "ctrl1@lvm",
                "zone": "nova", "status": "enabled", "state": "up",
                "updated_at": "2026-01-01T00:00:00Z", "disabled_reason": None, **kw}

    def test_list(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"services": [self._svc()]}
        result = invoke(["volume", "service-list"])
        assert result.exit_code == 0
        assert "cinder-" in result.output

    def test_list_filter_host(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"services": []}
        invoke(["volume", "service-list", "--host", "ctrl1"])
        assert mock_client.get.call_args[1]["params"]["host"] == "ctrl1"

    def test_list_filter_binary(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"services": []}
        invoke(["volume", "service-list", "--binary", "cinder-scheduler"])
        assert mock_client.get.call_args[1]["params"]["binary"] == "cinder-scheduler"

    def test_list_empty(self, invoke, mock_client):
        _vol(mock_client)
        mock_client.get.return_value = {"services": []}
        result = invoke(["volume", "service-list"])
        assert "No Cinder services" in result.output

    def test_help(self, invoke):
        assert invoke(["volume", "service-list", "--help"]).exit_code == 0


class TestVolumeServiceSet:

    def test_enable(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "service-set", "ctrl1", "cinder-volume", "--enable"])
        assert result.exit_code == 0
        url = mock_client.put.call_args[0][0]
        assert "/os-services/enable" in url

    def test_disable(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "service-set", "ctrl1", "cinder-volume", "--disable"])
        url = mock_client.put.call_args[0][0]
        assert "/os-services/disable" in url

    def test_disable_with_reason(self, invoke, mock_client):
        _vol(mock_client)
        invoke(["volume", "service-set", "ctrl1", "cinder-volume",
                "--disable", "--disabled-reason", "maintenance"])
        url = mock_client.put.call_args[0][0]
        assert "disable-log-reason" in url
        body = mock_client.put.call_args[1]["json"]
        assert body["disabled_reason"] == "maintenance"

    def test_no_action_error(self, invoke, mock_client):
        _vol(mock_client)
        result = invoke(["volume", "service-set", "ctrl1", "cinder-volume"])
        assert result.exit_code != 0

    def test_help(self, invoke):
        assert invoke(["volume", "service-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.parametrize("sub", [
        "set", "unset",
        "snapshot-set",
        "type-list", "type-show", "type-create", "type-set", "type-delete",
        "type-access-list", "type-access-add", "type-access-remove",
        "transfer-create", "transfer-list", "transfer-show",
        "transfer-accept", "transfer-delete",
        "qos-list", "qos-show", "qos-create", "qos-set", "qos-delete",
        "qos-associate", "qos-disassociate",
        "service-list", "service-set",
    ])
    def test_subcommand_help(self, invoke, sub):
        result = invoke(["volume", sub, "--help"])
        assert result.exit_code == 0, f"'volume {sub} --help' failed: {result.output}"
