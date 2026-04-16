"""Tests for ``orca floating-ip`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

FIP_ID = "11112222-3333-4444-5555-666677778888"
FIP_ID2 = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
PORT_ID = "99998888-7777-6666-5555-444433332222"
NET_ID = "abcdabcd-1234-5678-9abc-def012345678"
QOS_ID = "dd445566-7788-99aa-bbcc-ddeeff001122"


def _fip(fip_id=FIP_ID, ip="203.0.113.10", status="ACTIVE",
         port_id=PORT_ID, fixed_ip="10.0.0.5"):
    return {
        "id": fip_id,
        "floating_ip_address": ip,
        "fixed_ip_address": fixed_ip,
        "floating_network_id": NET_ID,
        "port_id": port_id,
        "router_id": "rtr-1",
        "status": status,
        "created_at": "2025-01-01T00:00:00Z",
    }


def _setup_mock(mock_client, fips=None, fip_detail=None):
    fips = fips if fips is not None else []
    mock_client.network_url = "https://neutron.example.com"

    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if FIP_ID in url or FIP_ID2 in url:
            return {"floatingip": fip_detail or (_fip() if fips else {})}
        if "floatingips" in url:
            return {"floatingips": fips}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        return {"floatingip": {"id": "new-fip", "floating_ip_address": "203.0.113.99"}}

    def _put(url, **kwargs):
        body = kwargs.get("json", {})
        put_data.update(body)
        return {"floatingip": {}}

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_data": put_data, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip list
# ══════════════════════════════════════════════════════════════════════════


class TestFipList:

    def test_list_fips(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[
            _fip(),
            _fip(fip_id=FIP_ID2, ip="203.0.113.20", status="DOWN", port_id=None, fixed_ip=None),
        ])

        result = invoke(["floating-ip", "list"])
        assert result.exit_code == 0
        assert "203.0" in result.output
        assert "ACTIVE" in result.output
        assert "DOWN" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[])

        result = invoke(["floating-ip", "list"])
        assert result.exit_code == 0
        assert "No floating IPs found" in result.output

    def test_list_shows_status(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[_fip(status="ACTIVE")])

        result = invoke(["floating-ip", "list"])
        assert "ACTIVE" in result.output

    def test_list_unassociated_shows_dash(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[_fip(port_id=None, fixed_ip=None)])

        result = invoke(["floating-ip", "list"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip show
# ══════════════════════════════════════════════════════════════════════════


class TestFipShow:

    def test_show_fip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fip_detail=_fip())

        result = invoke(["floating-ip", "show", FIP_ID])
        assert result.exit_code == 0
        assert "203.0.113" in result.output

    def test_show_displays_status(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fip_detail=_fip(status="DOWN"))

        result = invoke(["floating-ip", "show", FIP_ID])
        assert "DOWN" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip create
# ══════════════════════════════════════════════════════════════════════════


class TestFipCreate:

    def test_create_fip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "create", "--network", NET_ID])
        assert result.exit_code == 0
        assert "203.0.113.99" in result.output
        assert state["posted"]["floatingip"]["floating_network_id"] == NET_ID

    def test_create_requires_network(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["floating-ip", "create"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip delete
# ══════════════════════════════════════════════════════════════════════════


class TestFipDelete:

    def test_delete_fip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "delete", FIP_ID, "-y"])
        assert result.exit_code == 0
        assert "released" in result.output.lower()
        assert any(FIP_ID in u for u in state["deleted"])

    def test_delete_aborts_without_confirm(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "delete", FIP_ID], input="n\n")
        assert len(state["deleted"]) == 0


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip associate / disassociate
# ══════════════════════════════════════════════════════════════════════════


class TestFipAssociate:

    def test_associate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "associate", FIP_ID, "--port-id", PORT_ID])
        assert result.exit_code == 0
        assert "associated" in result.output.lower()
        assert state["put_data"]["floatingip"]["port_id"] == PORT_ID

    def test_associate_with_fixed_ip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "associate", FIP_ID,
                         "--port-id", PORT_ID, "--fixed-ip", "10.0.0.99"])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["fixed_ip_address"] == "10.0.0.99"

    def test_associate_requires_port_id(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["floating-ip", "associate", FIP_ID])
        assert result.exit_code != 0

    def test_disassociate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "disassociate", FIP_ID])
        assert result.exit_code == 0
        assert "disassociated" in result.output.lower()
        assert state["put_data"]["floatingip"]["port_id"] is None


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip set
# ══════════════════════════════════════════════════════════════════════════


class TestFipSet:

    def test_set_port(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID, "--port", PORT_ID])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
        assert state["put_data"]["floatingip"]["port_id"] == PORT_ID

    def test_set_description(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID, "--description", "my fip"])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["description"] == "my fip"

    def test_set_qos_policy(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID, "--qos-policy", QOS_ID])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["qos_policy_id"] == QOS_ID

    def test_set_no_qos_policy(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID, "--no-qos-policy"])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["qos_policy_id"] is None

    def test_set_qos_and_no_qos_mutually_exclusive(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID,
                         "--qos-policy", QOS_ID, "--no-qos-policy"])
        assert result.exit_code != 0

    def test_set_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["floating-ip", "set", FIP_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip unset
# ══════════════════════════════════════════════════════════════════════════


class TestFipUnset:

    def test_unset_port(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "unset", FIP_ID, "--port"])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["port_id"] is None

    def test_unset_qos_policy(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["floating-ip", "unset", FIP_ID, "--qos-policy"])
        assert result.exit_code == 0
        assert state["put_data"]["floatingip"]["qos_policy_id"] is None

    def test_unset_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["floating-ip", "unset", FIP_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  floating-ip bulk-release
# ══════════════════════════════════════════════════════════════════════════


class TestFipBulkRelease:

    def test_bulk_release_down(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client, fips=[
            _fip(status="DOWN", port_id=None),
            _fip(fip_id=FIP_ID2, ip="203.0.113.20", status="ACTIVE"),
        ])

        result = invoke(["floating-ip", "bulk-release", "-y"])
        assert result.exit_code == 0
        assert "1 released" in result.output
        assert len(state["deleted"]) == 1

    def test_bulk_release_by_status(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client, fips=[
            _fip(status="ERROR"),
            _fip(fip_id=FIP_ID2, ip="203.0.113.20", status="ERROR"),
        ])

        result = invoke(["floating-ip", "bulk-release", "--status", "ERROR", "-y"])
        assert result.exit_code == 0
        assert "2 released" in result.output

    def test_bulk_release_unassociated(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client, fips=[
            _fip(port_id=None, status="ACTIVE"),
            _fip(fip_id=FIP_ID2, ip="203.0.113.20", port_id=PORT_ID, status="ACTIVE"),
        ])

        result = invoke(["floating-ip", "bulk-release", "-u", "-y"])
        assert result.exit_code == 0
        assert "1 released" in result.output

    def test_bulk_release_no_matches(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, fips=[_fip(status="ACTIVE")])

        result = invoke(["floating-ip", "bulk-release", "-y"])
        assert result.exit_code == 0
        assert "No floating IPs matching" in result.output

    def test_bulk_release_aborts_without_confirm(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client, fips=[_fip(status="DOWN")])

        result = invoke(["floating-ip", "bulk-release"], input="n\n")
        assert len(state["deleted"]) == 0

    def test_bulk_release_handles_failure(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.network_url = "https://neutron.example.com"

        mock_client.get = lambda url, **kw: {"floatingips": [
            _fip(status="DOWN"),
        ]}
        mock_client.delete = lambda url, **kw: (_ for _ in ()).throw(Exception("forbidden"))

        result = invoke(["floating-ip", "bulk-release", "-y"])
        assert result.exit_code == 0
        assert "1 failed" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestFipHelp:

    def test_floating_ip_help(self, invoke):
        result = invoke(["floating-ip", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "associate", "disassociate",
                    "set", "unset", "bulk-release"):
            assert cmd in result.output

    def test_list_help(self, invoke):
        result = invoke(["floating-ip", "list", "--help"])
        assert result.exit_code == 0

    def test_bulk_release_help(self, invoke):
        result = invoke(["floating-ip", "bulk-release", "--help"])
        assert result.exit_code == 0
        assert "--status" in result.output
        assert "--unassociated" in result.output
