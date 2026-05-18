"""Tests for ``orca share`` (Manila) commands."""

from __future__ import annotations

import pytest

MANILA = "https://share.example.com/v2"
SHARE_ID = "11111111-1111-1111-1111-111111111111"
ACCESS_ID = "22222222-2222-2222-2222-222222222222"
SNAP_ID = "33333333-3333-3333-3333-333333333333"
TYPE_ID = "44444444-4444-4444-4444-444444444444"


@pytest.fixture(autouse=True)
def _wire(mock_client):
    mock_client.share_url = MANILA


# ── registration ──────────────────────────────────────────────────────

class TestRegistration:

    def test_share_help(self, invoke):
        result = invoke(["share", "--help"])
        assert result.exit_code == 0
        for sub in ("list", "show", "create", "set", "delete", "extend",
                    "shrink", "access", "snapshot", "type"):
            assert sub in result.output

    @pytest.mark.parametrize("path", [
        ["share", "list", "--help"],
        ["share", "show", "--help"],
        ["share", "create", "--help"],
        ["share", "delete", "--help"],
        ["share", "set", "--help"],
        ["share", "extend", "--help"],
        ["share", "shrink", "--help"],
        ["share", "access", "--help"],
        ["share", "access", "list", "--help"],
        ["share", "access", "allow", "--help"],
        ["share", "access", "deny", "--help"],
        ["share", "snapshot", "--help"],
        ["share", "snapshot", "list", "--help"],
        ["share", "snapshot", "show", "--help"],
        ["share", "snapshot", "create", "--help"],
        ["share", "snapshot", "delete", "--help"],
        ["share", "type", "--help"],
        ["share", "type", "list", "--help"],
        ["share", "type", "show", "--help"],
    ])
    def test_subcommand_help(self, invoke, path):
        assert invoke(path).exit_code == 0


# ── share list/show/create/delete/set ─────────────────────────────────

class TestShareList:

    def test_list_renders(self, invoke, mock_client):
        mock_client.get.return_value = {"shares": [{
            "id": SHARE_ID, "name": "my-nfs", "status": "available",
            "size": 50, "share_proto": "NFS", "share_type_name": "default",
            "availability_zone": "az1",
        }]}
        result = invoke(["share", "list", "-f", "value", "-c", "Name"])
        assert result.exit_code == 0
        assert "my-nfs" in result.output

    def test_list_empty(self, invoke, mock_client):
        mock_client.get.return_value = {"shares": []}
        result = invoke(["share", "list"])
        assert result.exit_code == 0
        assert "No shares" in result.output


class TestShareShow:

    def test_show_unwraps_envelope(self, invoke, mock_client):
        mock_client.get.return_value = {"share": {
            "id": SHARE_ID, "name": "my-nfs", "size": 50, "status": "available",
            "share_proto": "NFS", "export_locations": [{"path": "10.0.0.1:/shares/abc"}],
        }}
        result = invoke(["share", "show", SHARE_ID, "-f", "value"])
        assert result.exit_code == 0
        assert "10.0.0.1:/shares/abc" in result.output


class TestShareCreate:

    def test_create_minimum(self, invoke, mock_client):
        mock_client.post.return_value = {"share": {"id": SHARE_ID, "name": "n"}}
        result = invoke(["share", "create", "n", "--size", "10"])
        assert result.exit_code == 0
        body = mock_client.post.call_args.kwargs["json"]["share"]
        assert body["name"] == "n"
        assert body["size"] == 10
        assert body["share_proto"] == "NFS"
        assert body["is_public"] is False

    def test_create_full_options(self, invoke, mock_client):
        mock_client.post.return_value = {"share": {"id": SHARE_ID}}
        invoke(["share", "create", "n", "--size", "50", "--protocol", "CEPHFS",
                "--description", "desc", "--share-type", "default",
                "--share-network", "net-1", "--availability-zone", "az1",
                "--public"])
        body = mock_client.post.call_args.kwargs["json"]["share"]
        assert body["share_proto"] == "CEPHFS"
        assert body["description"] == "desc"
        assert body["share_type"] == "default"
        assert body["share_network_id"] == "net-1"
        assert body["availability_zone"] == "az1"
        assert body["is_public"] is True

    def test_create_from_snapshot(self, invoke, mock_client):
        mock_client.post.return_value = {"share": {"id": SHARE_ID}}
        invoke(["share", "create", "n", "--size", "10", "--snapshot-id", SNAP_ID])
        body = mock_client.post.call_args.kwargs["json"]["share"]
        assert body["snapshot_id"] == SNAP_ID

    def test_create_rejects_unknown_protocol(self, invoke, mock_client):
        result = invoke(["share", "create", "n", "--size", "10", "--protocol", "BOGUS"])
        assert result.exit_code != 0


class TestShareSet:

    def test_set_name_and_description(self, invoke, mock_client):
        mock_client.put.return_value = {"share": {"id": SHARE_ID}}
        invoke(["share", "set", SHARE_ID, "--name", "newname",
                "--description", "newdesc"])
        body = mock_client.put.call_args.kwargs["json"]["share"]
        assert body["display_name"] == "newname"
        assert body["display_description"] == "newdesc"

    def test_set_visibility_only(self, invoke, mock_client):
        mock_client.put.return_value = {"share": {"id": SHARE_ID}}
        invoke(["share", "set", SHARE_ID, "--public"])
        body = mock_client.put.call_args.kwargs["json"]["share"]
        assert body == {"is_public": True}

    def test_set_nothing_short_circuits(self, invoke, mock_client):
        result = invoke(["share", "set", SHARE_ID])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()
        assert "Nothing to update" in result.output


class TestShareDelete:

    def test_delete_yes(self, invoke, mock_client):
        result = invoke(["share", "delete", SHARE_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        result = invoke(["share", "delete", SHARE_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()


class TestShareExtendShrink:

    def test_extend(self, invoke, mock_client):
        invoke(["share", "extend", SHARE_ID, "--size", "20"])
        body = mock_client.post.call_args.kwargs["json"]
        assert body == {"extend": {"new_size": 20}}

    def test_shrink(self, invoke, mock_client):
        invoke(["share", "shrink", SHARE_ID, "--size", "5"])
        body = mock_client.post.call_args.kwargs["json"]
        assert body == {"shrink": {"new_size": 5}}


# ── access rules ─────────────────────────────────────────────────────

class TestShareAccess:

    def test_list(self, invoke, mock_client):
        mock_client.get.return_value = {"access_list": [{
            "id": ACCESS_ID, "access_type": "ip", "access_to": "10.0.0.0/24",
            "access_level": "rw", "state": "active",
        }]}
        result = invoke(["share", "access", "list", SHARE_ID, "-f", "value"])
        assert result.exit_code == 0
        assert "10.0.0.0/24" in result.output

    def test_allow_ip(self, invoke, mock_client):
        mock_client.post.return_value = {"access": {"id": ACCESS_ID}}
        result = invoke(["share", "access", "allow", SHARE_ID,
                         "--access-type", "ip", "--access-to", "10.0.0.0/24"])
        assert result.exit_code == 0
        body = mock_client.post.call_args.kwargs["json"]["allow_access"]
        assert body == {"access_type": "ip", "access_to": "10.0.0.0/24", "access_level": "rw"}

    def test_allow_cephx_surfaces_access_key(self, invoke, mock_client):
        mock_client.post.return_value = {"access": {
            "id": ACCESS_ID, "access_key": "AQABCD==",
        }}
        result = invoke(["share", "access", "allow", SHARE_ID,
                         "--access-type", "cephx", "--access-to", "client.foo"])
        assert result.exit_code == 0
        assert "AQABCD==" in result.output

    def test_allow_rejects_invalid_type(self, invoke, mock_client):
        result = invoke(["share", "access", "allow", SHARE_ID,
                         "--access-type", "bogus", "--access-to", "x"])
        assert result.exit_code != 0

    def test_deny_yes(self, invoke, mock_client):
        result = invoke(["share", "access", "deny", SHARE_ID, ACCESS_ID, "--yes"])
        assert result.exit_code == 0
        body = mock_client.post.call_args.kwargs["json"]
        assert body == {"deny_access": {"access_id": ACCESS_ID}}


# ── snapshots ────────────────────────────────────────────────────────

class TestShareSnapshot:

    def test_list(self, invoke, mock_client):
        mock_client.get.return_value = {"snapshots": [{
            "id": SNAP_ID, "name": "daily", "status": "available",
            "share_id": SHARE_ID, "size": 50, "created_at": "2026-04-28T00:00:00Z",
        }]}
        result = invoke(["share", "snapshot", "list", "-f", "value", "-c", "Name"])
        assert result.exit_code == 0
        assert "daily" in result.output

    def test_show(self, invoke, mock_client):
        mock_client.get.return_value = {"snapshot": {
            "id": SNAP_ID, "name": "daily", "status": "available",
            "share_id": SHARE_ID, "size": 50,
        }}
        result = invoke(["share", "snapshot", "show", SNAP_ID, "-f", "value"])
        assert result.exit_code == 0
        assert SHARE_ID in result.output

    def test_create_minimum(self, invoke, mock_client):
        mock_client.post.return_value = {"snapshot": {"id": SNAP_ID}}
        invoke(["share", "snapshot", "create", SHARE_ID])
        body = mock_client.post.call_args.kwargs["json"]["snapshot"]
        assert body == {"share_id": SHARE_ID}

    def test_create_with_name(self, invoke, mock_client):
        mock_client.post.return_value = {"snapshot": {"id": SNAP_ID}}
        invoke(["share", "snapshot", "create", SHARE_ID, "--name", "daily"])
        body = mock_client.post.call_args.kwargs["json"]["snapshot"]
        assert body == {"share_id": SHARE_ID, "name": "daily"}

    def test_delete_yes(self, invoke, mock_client):
        invoke(["share", "snapshot", "delete", SNAP_ID, "--yes"])
        mock_client.delete.assert_called_once()


# ── types ────────────────────────────────────────────────────────────

class TestShareType:

    def test_list(self, invoke, mock_client):
        mock_client.get.return_value = {"share_types": [{
            "id": TYPE_ID, "name": "default", "is_default": True,
            "is_public": True, "extra_specs": {"snapshot_support": "True"},
        }]}
        result = invoke(["share", "type", "list", "-f", "value", "-c", "Name"])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_show(self, invoke, mock_client):
        mock_client.get.return_value = {"share_type": {
            "id": TYPE_ID, "name": "default", "is_default": True,
            "extra_specs": {"snapshot_support": "True"},
            "required_extra_specs": {"driver_handles_share_servers": "False"},
        }}
        # ``json`` format keeps both keys and values intact.
        result = invoke(["share", "type", "show", TYPE_ID, "-f", "json"])
        assert result.exit_code == 0
        assert "snapshot_support" in result.output
        assert "driver_handles_share_servers" in result.output


# ── client.share_url catalog fallback ────────────────────────────────

class TestShareUrlCatalogFallback:
    """``client.share_url`` accepts both ``sharev2`` and ``share`` types."""

    def test_prefers_sharev2(self):
        from orca_cli.core.client import OrcaClient
        client = OrcaClient.__new__(OrcaClient)
        client._catalog = [
            {"type": "sharev2", "endpoints": [{"interface": "public",
                                                "url": "https://sharev2.example/v2"}]},
            {"type": "share", "endpoints": [{"interface": "public",
                                              "url": "https://legacy.example/v1"}]},
        ]
        client._region_name = None
        client._interface = "public"
        assert client.share_url == "https://sharev2.example/v2"

    def test_falls_back_to_share(self):
        from orca_cli.core.client import OrcaClient
        client = OrcaClient.__new__(OrcaClient)
        client._catalog = [
            {"type": "share", "endpoints": [{"interface": "public",
                                              "url": "https://legacy.example/v1"}]},
        ]
        client._region_name = None
        client._interface = "public"
        assert client.share_url == "https://legacy.example/v1"

    def test_raises_when_absent(self):
        from orca_cli.core.client import APIError, OrcaClient
        client = OrcaClient.__new__(OrcaClient)
        client._catalog = []
        client._region_name = None
        client._interface = "public"
        with pytest.raises(APIError):
            _ = client.share_url
