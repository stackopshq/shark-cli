"""Tests for Nova admin commands: compute-service, server migration-*, flavor access-*."""

from __future__ import annotations

import pytest

SRV = "11111111-1111-1111-1111-111111111111"
FLV = "22222222-2222-2222-2222-222222222222"
PRJ = "33333333-3333-3333-3333-333333333333"
NOVA = "https://nova.example.com/v2.1"


def _nova(mock_client):
    mock_client.compute_url = NOVA
    return mock_client


# ══════════════════════════════════════════════════════════════════════════
#  compute-service list
# ══════════════════════════════════════════════════════════════════════════

class TestComputeServiceList:

    def _svc(self, **kw):
        return {"id": 1, "binary": "nova-compute", "host": "host1",
                "zone": "nova", "status": "enabled", "state": "up",
                "updated_at": "2026-01-01T00:00:00Z", "disabled_reason": None, **kw}

    def test_list(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"services": [self._svc()]}
        result = invoke(["compute-service", "list"])
        assert result.exit_code == 0
        assert "nova-" in result.output
        assert "host1" in result.output

    def test_list_filter_host(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"services": []}
        invoke(["compute-service", "list", "--host", "host2"])
        assert mock_client.get.call_args[1]["params"]["host"] == "host2"

    def test_list_filter_binary(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"services": []}
        invoke(["compute-service", "list", "--binary", "nova-conductor"])
        assert mock_client.get.call_args[1]["params"]["binary"] == "nova-conductor"

    def test_list_shows_disabled_state(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"services": [
            self._svc(status="disabled", disabled_reason="maintenance")
        ]}
        result = invoke(["compute-service", "list"])
        assert result.exit_code == 0
        assert "disabled" in result.output.lower()

    def test_list_empty(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"services": []}
        result = invoke(["compute-service", "list"])
        assert "No compute services" in result.output

    def test_help(self, invoke):
        assert invoke(["compute-service", "list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  compute-service set
# ══════════════════════════════════════════════════════════════════════════

class TestComputeServiceSet:

    def test_disable(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["compute-service", "set", "1", "--disable"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["status"] == "disabled"

    def test_enable(self, invoke, mock_client):
        _nova(mock_client)
        invoke(["compute-service", "set", "1", "--enable"])
        body = mock_client.put.call_args[1]["json"]
        assert body["status"] == "enabled"

    def test_disable_with_reason(self, invoke, mock_client):
        _nova(mock_client)
        invoke(["compute-service", "set", "1", "--disable",
                "--disabled-reason", "hardware failure"])
        body = mock_client.put.call_args[1]["json"]
        assert body["status"] == "disabled"
        assert body["disabled_reason"] == "hardware failure"

    def test_force_down(self, invoke, mock_client):
        _nova(mock_client)
        invoke(["compute-service", "set", "1", "--force-down"])
        body = mock_client.put.call_args[1]["json"]
        assert body["forced_down"] is True

    def test_nothing_to_update(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["compute-service", "set", "1"])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_calls_correct_url(self, invoke, mock_client):
        _nova(mock_client)
        invoke(["compute-service", "set", "42", "--enable"])
        url = mock_client.put.call_args[0][0]
        assert "/os-services/42" in url

    def test_help(self, invoke):
        assert invoke(["compute-service", "set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  compute-service delete
# ══════════════════════════════════════════════════════════════════════════

class TestComputeServiceDelete:

    def test_delete_yes(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["compute-service", "delete", "1", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        assert "/os-services/1" in mock_client.delete.call_args[0][0]

    def test_delete_requires_confirm(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["compute-service", "delete", "1"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["compute-service", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  server migration-list
# ══════════════════════════════════════════════════════════════════════════

class TestServerMigrationList:

    def _migration(self, **kw):
        return {"id": 10, "migration_type": "live-migration",
                "status": "completed", "source_compute": "host1",
                "dest_compute": "host2", "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:01:00Z", **kw}

    def test_list(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migrations": [self._migration()]}
        result = invoke(["server", "migration-list", SRV])
        assert result.exit_code == 0
        assert "host1" in result.output
        assert "host2" in result.output

    def test_list_calls_correct_url(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migrations": []}
        invoke(["server", "migration-list", SRV])
        url = mock_client.get.call_args[0][0]
        assert f"/servers/{SRV}/migrations" in url

    def test_list_empty(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migrations": []}
        result = invoke(["server", "migration-list", SRV])
        assert result.exit_code == 0
        assert "No migrations" in result.output

    def test_shows_migration_type(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migrations": [
            self._migration(migration_type="cold-migration")
        ]}
        result = invoke(["server", "migration-list", SRV])
        assert "cold" in result.output.lower()

    def test_help(self, invoke):
        assert invoke(["server", "migration-list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  server migration-show
# ══════════════════════════════════════════════════════════════════════════

class TestServerMigrationShow:

    def test_show(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migration": {
            "id": 10, "migration_type": "live-migration", "status": "completed",
            "source_compute": "host1", "source_node": "node1",
            "dest_compute": "host2", "dest_node": "node2",
            "old_instance_type_id": FLV, "new_instance_type_id": FLV,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:01:00Z",
        }}
        result = invoke(["server", "migration-show", SRV, "10"])
        assert result.exit_code == 0
        assert "completed" in result.output

    def test_show_calls_correct_url(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"migration": {}}
        invoke(["server", "migration-show", SRV, "10"])
        url = mock_client.get.call_args[0][0]
        assert f"/servers/{SRV}/migrations/10" in url

    def test_help(self, invoke):
        assert invoke(["server", "migration-show", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  flavor access-list
# ══════════════════════════════════════════════════════════════════════════

class TestFlavorAccessList:

    def test_list(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"flavor_access": [
            {"flavor_id": FLV, "tenant_id": PRJ},
        ]}
        result = invoke(["flavor", "access-list", FLV])
        assert result.exit_code == 0
        assert PRJ[:8] in result.output

    def test_list_calls_correct_url(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"flavor_access": []}
        invoke(["flavor", "access-list", FLV])
        url = mock_client.get.call_args[0][0]
        assert f"/flavors/{FLV}/os-flavor-access" in url

    def test_list_empty(self, invoke, mock_client):
        _nova(mock_client)
        mock_client.get.return_value = {"flavor_access": []}
        result = invoke(["flavor", "access-list", FLV])
        assert result.exit_code == 0
        assert "No access" in result.output or "public" in result.output.lower()

    def test_help(self, invoke):
        assert invoke(["flavor", "access-list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  flavor access-add
# ══════════════════════════════════════════════════════════════════════════

class TestFlavorAccessAdd:

    def test_add(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["flavor", "access-add", FLV, PRJ])
        assert result.exit_code == 0
        assert mock_client.post.called
        body = mock_client.post.call_args[1]["json"]
        assert body["addTenantAccess"]["tenant"] == PRJ

    def test_add_calls_correct_url(self, invoke, mock_client):
        _nova(mock_client)
        invoke(["flavor", "access-add", FLV, PRJ])
        url = mock_client.post.call_args[0][0]
        assert f"/flavors/{FLV}/action" in url

    def test_help(self, invoke):
        assert invoke(["flavor", "access-add", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  flavor access-remove
# ══════════════════════════════════════════════════════════════════════════

class TestFlavorAccessRemove:

    def test_remove_yes(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["flavor", "access-remove", FLV, PRJ, "--yes"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["removeTenantAccess"]["tenant"] == PRJ

    def test_remove_requires_confirm(self, invoke, mock_client):
        _nova(mock_client)
        result = invoke(["flavor", "access-remove", FLV, PRJ], input="n\n")
        assert result.exit_code != 0
        mock_client.post.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["flavor", "access-remove", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════

class TestRegistration:

    def test_compute_service_registered(self, invoke):
        assert invoke(["compute-service", "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["list", "set", "delete"])
    def test_compute_service_subcommands(self, invoke, sub):
        assert invoke(["compute-service", sub, "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["migration-list", "migration-show"])
    def test_server_migration_subcommands(self, invoke, sub):
        assert invoke(["server", sub, "--help"]).exit_code == 0

    @pytest.mark.parametrize("sub", ["access-list", "access-add", "access-remove"])
    def test_flavor_access_subcommands(self, invoke, sub):
        assert invoke(["flavor", sub, "--help"]).exit_code == 0
