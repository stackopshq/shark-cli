"""Tests for ``orca project cleanup`` — router/network helpers + outcome classification."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.commands import project as proj_mod
from orca_cli.commands.project import Outcome
from orca_cli.core.exceptions import APIError


def _make_net_svc(monkeypatch, **attrs):
    net_svc = MagicMock()
    for k, v in attrs.items():
        setattr(net_svc, k, v)
    monkeypatch.setattr(proj_mod, "NetworkService", lambda _c: net_svc)
    return net_svc


class TestDeleteRouter:
    def test_clears_gateway_before_detaching_and_deleting(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = []

        proj_mod._delete_router(object(), "r-1")

        net.update_router.assert_called_once_with(
            "r-1", {"external_gateway_info": None}
        )
        net.delete_router.assert_called_once_with("r-1")

    def test_detaches_all_router_interface_flavors(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = [
            {"id": "p-legacy", "device_owner": "network:router_interface"},
            {"id": "p-dvr",
             "device_owner": "network:router_interface_distributed"},
            {"id": "p-ha",
             "device_owner": "network:ha_router_replicated_interface"},
        ]

        proj_mod._delete_router(object(), "r-1")

        assert net.remove_router_interface.call_count == 3
        detached = {
            c.args[1]["port_id"]
            for c in net.remove_router_interface.call_args_list
        }
        assert detached == {"p-legacy", "p-dvr", "p-ha"}

    def test_ignores_non_interface_ports(self, monkeypatch):
        """Gateway / SNAT / foreign ports must not go through remove_router_interface."""
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = [
            {"id": "p-gw", "device_owner": "network:router_gateway"},
            {"id": "p-snat", "device_owner": "network:router_centralized_snat"},
            {"id": "p-dhcp", "device_owner": "network:dhcp"},
            {"id": "p-orphan", "device_owner": ""},
        ]

        proj_mod._delete_router(object(), "r-1")

        net.remove_router_interface.assert_not_called()
        net.delete_router.assert_called_once_with("r-1")

    def test_lists_ports_by_device_id_only(self, monkeypatch):
        """Broader filter: device_owner is applied Python-side, not in the query."""
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = []

        proj_mod._delete_router(object(), "r-xyz")

        net.find_ports.assert_called_once_with(params={"device_id": "r-xyz"})

    def test_continues_when_update_router_fails(self, monkeypatch):
        """Some clouds reject gateway clear if no gateway set — must not abort."""
        net = _make_net_svc(monkeypatch)
        net.update_router.side_effect = RuntimeError("no gateway")
        net.find_ports.return_value = [
            {"id": "p1", "device_owner": "network:router_interface"},
        ]

        proj_mod._delete_router(object(), "r-1")

        net.remove_router_interface.assert_called_once_with(
            "r-1", {"port_id": "p1"}
        )
        net.delete_router.assert_called_once_with("r-1")

    def test_continues_when_find_ports_fails(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.side_effect = RuntimeError("neutron down")

        proj_mod._delete_router(object(), "r-1")

        net.remove_router_interface.assert_not_called()
        net.delete_router.assert_called_once_with("r-1")

    def test_continues_when_remove_interface_fails(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = [
            {"id": "p1", "device_owner": "network:router_interface"},
            {"id": "p2", "device_owner": "network:router_interface"},
        ]
        net.remove_router_interface.side_effect = [RuntimeError("boom"), None]

        proj_mod._delete_router(object(), "r-1")

        assert net.remove_router_interface.call_count == 2
        net.delete_router.assert_called_once_with("r-1")


class TestDeleteNetwork:
    def test_deletes_orphan_and_stale_compute_ports(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = [
            {"id": "p-orphan", "device_owner": ""},
            {"id": "p-vif", "device_owner": "compute:nova"},
            {"id": "p-dhcp", "device_owner": "network:dhcp"},
            {"id": "p-router", "device_owner": "network:router_interface"},
            {"id": "p-fip", "device_owner": "network:floatingip"},
        ]

        proj_mod._delete_network(object(), "n-1")

        deleted = {c.args[0] for c in net.delete_port.call_args_list}
        assert deleted == {"p-orphan", "p-vif"}
        net.delete.assert_called_once_with("n-1")

    def test_lists_ports_by_network_id(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = []

        proj_mod._delete_network(object(), "n-42")

        net.find_ports.assert_called_once_with(params={"network_id": "n-42"})
        net.delete.assert_called_once_with("n-42")

    def test_continues_when_port_delete_fails(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.return_value = [
            {"id": "p1", "device_owner": ""},
            {"id": "p2", "device_owner": "compute:nova"},
        ]
        net.delete_port.side_effect = [RuntimeError("boom"), None]

        proj_mod._delete_network(object(), "n-1")

        assert net.delete_port.call_count == 2
        net.delete.assert_called_once_with("n-1")

    def test_continues_when_find_ports_fails(self, monkeypatch):
        net = _make_net_svc(monkeypatch)
        net.find_ports.side_effect = RuntimeError("neutron down")

        proj_mod._delete_network(object(), "n-1")

        net.delete_port.assert_not_called()
        net.delete.assert_called_once_with("n-1")


def _svc_that_raises(monkeypatch, service_attr: str, exc: Exception) -> MagicMock:
    """Replace one Service class on the project module so its delete raises exc."""
    svc = MagicMock()
    # Configure every delete-like method to raise. project._delete_one picks one
    # depending on rtype; this avoids us caring which method name gets called.
    for name in ("delete", "delete_router", "delete_floating_ip",
                 "delete_security_group", "delete_snapshot", "delete_backup",
                 "delete_secret", "delete_zone", "delete_container",
                 "delete_port"):
        getattr(svc, name).side_effect = exc
    # For the network router helper we also need find_ports / update_router /
    # remove_router_interface to not blow up before the final delete_router.
    svc.find_ports.return_value = []
    svc.update_router.return_value = None
    svc.remove_router_interface.return_value = None
    monkeypatch.setattr(proj_mod, service_attr, lambda _c: svc)
    return svc


class TestClassifyApiError:
    @pytest.mark.parametrize("status,expected", [
        (404, Outcome.ALREADY_GONE),
        (409, Outcome.BLOCKED),
        (400, Outcome.FAILED),
        (500, Outcome.FAILED),
        (401, Outcome.FAILED),
    ])
    def test_status_to_outcome(self, status, expected):
        assert proj_mod._classify_api_error(APIError(status, "detail")) is expected


class TestDeleteOneOutcomes:
    """_delete_one must map HTTP status to the right Outcome."""

    def test_success_path_returns_success(self, monkeypatch):
        svc = MagicMock()
        monkeypatch.setattr(proj_mod, "VolumeService", lambda _c: svc)
        out = proj_mod._delete_one(object(), "volume", "v-1", "—")
        assert out is Outcome.SUCCESS
        svc.delete.assert_called_once_with("v-1", cascade=True)

    def test_404_volume_is_already_gone(self, monkeypatch):
        _svc_that_raises(monkeypatch, "VolumeService",
                         APIError(404, "volume gone"))
        out = proj_mod._delete_one(object(), "volume", "v-1", "—")
        assert out is Outcome.ALREADY_GONE

    def test_404_server_is_already_gone(self, monkeypatch):
        _svc_that_raises(monkeypatch, "ServerService",
                         APIError(404, "server gone"))
        out = proj_mod._delete_one(object(), "server", "s-1", "web")
        assert out is Outcome.ALREADY_GONE

    def test_409_router_is_blocked(self, monkeypatch):
        _svc_that_raises(monkeypatch, "NetworkService",
                         APIError(409, "ports still attached"))
        out = proj_mod._delete_one(object(), "router", "r-1", "rtr")
        assert out is Outcome.BLOCKED

    def test_409_network_is_blocked(self, monkeypatch):
        _svc_that_raises(monkeypatch, "NetworkService",
                         APIError(409, "ports still in use"))
        out = proj_mod._delete_one(object(), "network", "n-1", "net")
        assert out is Outcome.BLOCKED

    def test_400_volume_in_use_is_failed(self, monkeypatch):
        """400 is a real client error, not a dependency block."""
        _svc_that_raises(monkeypatch, "VolumeService",
                         APIError(400, "status must be available"))
        out = proj_mod._delete_one(object(), "volume", "v-1", "—")
        assert out is Outcome.FAILED

    def test_unexpected_exception_is_failed(self, monkeypatch):
        _svc_that_raises(monkeypatch, "VolumeService",
                         RuntimeError("boom"))
        out = proj_mod._delete_one(object(), "volume", "v-1", "—")
        assert out is Outcome.FAILED


class TestSummaryRendering:
    """End-to-end through the Click command: the summary line must aggregate
    the four outcomes independently — a mix of 404s, 409s and real failures
    should not show as a monolithic fail count."""

    def test_summary_shows_four_categories(self, monkeypatch, mock_client, runner):
        from orca_cli.main import cli

        # Fake token_data so the command can resolve "current project".
        mock_client._token_data = {"project": {"id": "p-1"}}

        # Empty scan except for 4 volumes, one per Outcome.
        def fake_find(self, **kwargs):
            return []
        monkeypatch.setattr(proj_mod.IdentityService, "find_projects",
                            lambda self, **k: [])
        monkeypatch.setattr(proj_mod.IdentityService, "get_project",
                            lambda self, pid: {"id": pid})

        def vols(self, **kwargs):
            return [
                {"id": "ok", "name": "ok"},
                {"id": "gone", "name": "gone"},
                {"id": "blocked", "name": "blocked"},
                {"id": "broken", "name": "broken"},
            ]
        monkeypatch.setattr(proj_mod.VolumeService, "find", vols)
        # Neutralize other scans.
        for svc_cls, method in [
            (proj_mod.OrchestrationService, "find"),
            (proj_mod.LoadBalancerService, "find"),
            (proj_mod.ServerService, "find_all"),
            (proj_mod.NetworkService, "find_floating_ips"),
            (proj_mod.DnsService, "find_zones"),
            (proj_mod.NetworkService, "find_routers"),
            (proj_mod.NetworkService, "find"),
            (proj_mod.NetworkService, "find_security_groups"),
            (proj_mod.VolumeService, "find_snapshots"),
            (proj_mod.ImageService, "find"),
            (proj_mod.VolumeService, "find_backups"),
            (proj_mod.KeyManagerService, "find_secrets"),
            (proj_mod.ObjectStoreService, "find_containers"),
        ]:
            monkeypatch.setattr(svc_cls, method, fake_find)

        # One behavior per volume id.
        def vol_delete(self, vid, cascade=True):
            if vid == "ok":
                return
            if vid == "gone":
                raise APIError(404, "gone")
            if vid == "blocked":
                raise APIError(409, "in use")
            raise APIError(400, "bad state")
        monkeypatch.setattr(proj_mod.VolumeService, "delete", vol_delete)

        result = runner.invoke(cli, ["project", "cleanup", "--yes"])
        assert result.exit_code == 0, result.output
        assert "1 deleted" in result.output
        assert "1 already gone" in result.output
        assert "1 blocked" in result.output
        assert "1 failed" in result.output
        assert "(of 4)" in result.output
