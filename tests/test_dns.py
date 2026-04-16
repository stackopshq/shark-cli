"""Tests for zone and recordset commands (Designate)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

DNS_URL = "https://dns.example.com"


def _zone(zone_id="zone-1111-2222-3333-444444444444", name="example.com.",
          status="ACTIVE", ztype="PRIMARY", email="admin@example.com",
          ttl=3600, serial=1234567890):
    return {
        "id": zone_id, "name": name, "type": ztype, "status": status,
        "email": email, "ttl": ttl, "serial": serial,
        "pool_id": "pool-1", "project_id": "proj-1",
        "description": "Test zone", "masters": [],
        "created_at": "2025-01-01T00:00:00Z", "updated_at": None, "version": 1,
    }


def _recordset(rs_id="rs-1111-2222-3333-444444444444", name="www.example.com.",
               rtype="A", records=None, status="ACTIVE", ttl=300,
               zone_id="zone-1111-2222-3333-444444444444", zone_name="example.com."):
    return {
        "id": rs_id, "name": name, "type": rtype,
        "records": records or ["1.2.3.4"], "status": status, "ttl": ttl,
        "description": "", "zone_id": zone_id, "zone_name": zone_name,
        "created_at": "2025-01-01T00:00:00Z", "updated_at": None, "version": 1,
    }


def _setup_mock(mock_client, zones=None, recordsets=None, zone_detail=None):
    zones = zones or []
    recordsets = recordsets or []

    def _get(url, **kwargs):
        params = kwargs.get("params", {})
        if "/v2/zones" in url and "/recordsets" in url:
            return {"recordsets": recordsets, "links": {}}
        if "/v2/zones" in url:
            if any(c in url.split("/v2/zones/")[-1] for c in ["-"]) and "tasks" not in url:
                # Zone detail
                return zone_detail or (zones[0] if zones else _zone())
            # With name param = resolve query
            if params.get("name"):
                matches = [z for z in zones if z["name"] == params["name"]]
                return {"zones": matches}
            return {"zones": zones}
        return {}

    def _post(url, **kwargs):
        if "/v2/zones" in url and "/recordsets" in url:
            body = kwargs.get("json", {})
            return {"id": "new-rs-id", "name": body.get("name", ""), "type": body.get("type", "")}
        if "/v2/zones" in url:
            body = kwargs.get("json", {})
            return {"id": "new-zone-id", "name": body.get("name", "")}
        return {}

    def _patch(url, **kwargs):
        return {"id": "zone-1"}

    def _put(url, **kwargs):
        return {}

    def _delete(url, **kwargs):
        return None

    mock_client.get = _get
    mock_client.post = _post
    mock_client.patch = _patch
    mock_client.put = _put
    mock_client.delete = _delete
    mock_client.dns_url = DNS_URL


# ══════════════════════════════════════════════════════════════════════════
#  zone list
# ══════════════════════════════════════════════════════════════════════════


class TestZoneList:

    def test_list_zones(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone(), _zone(zone_id="z-2", name="other.com.")])

        result = invoke(["zone", "list"])
        assert result.exit_code == 0
        # Rich truncates in narrow test terminals; check partial matches
        assert "exa" in result.output
        assert "oth" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[])

        result = invoke(["zone", "list"])
        assert result.exit_code == 0
        assert "No DNS zones found" in result.output

    def test_list_shows_columns(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()])

        result = invoke(["zone", "list"])
        assert "3600" in result.output
        # Rich may truncate ACTIVE→ACTI… and email; just verify the table rendered
        assert "DNS Zones" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone show
# ══════════════════════════════════════════════════════════════════════════


class TestZoneShow:

    def test_show_by_id(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        z = _zone()
        _setup_mock(mock_client, zones=[z], zone_detail=z)

        result = invoke(["zone", "show", z["id"]])
        assert result.exit_code == 0
        assert "example.com." in result.output
        assert "ACTIVE" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone create
# ══════════════════════════════════════════════════════════════════════════


class TestZoneCreate:

    def test_create_zone(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["zone", "create", "test.com.", "--email", "a@b.com"])
        assert result.exit_code == 0
        assert "created" in result.output

    def test_create_zone_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        posted = {}

        def capture_post(url, **kwargs):
            posted.update(kwargs.get("json", {}))
            return {"id": "z-new", "name": "test.com."}

        _setup_mock(mock_client)
        mock_client.post = capture_post

        result = invoke(["zone", "create", "test.com.", "--email", "a@b.com",
                         "--ttl", "7200", "--description", "My zone"])
        assert result.exit_code == 0
        assert posted["ttl"] == 7200
        assert posted["description"] == "My zone"

    def test_create_zone_missing_dot(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["zone", "create", "test.com", "--email", "a@b.com"])
        assert result.exit_code != 0
        assert "dot" in result.output.lower() or "dot" in str(result.exception).lower()


# ══════════════════════════════════════════════════════════════════════════
#  zone set (formerly zone-update)
# ══════════════════════════════════════════════════════════════════════════


class TestZoneUpdate:

    def test_update_zone(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        patched = {}

        def capture_patch(url, **kwargs):
            patched.update(kwargs.get("json", {}))
            return {}

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.patch = capture_patch

        result = invoke(["zone", "set", _zone()["id"], "--ttl", "7200"])
        assert result.exit_code == 0
        assert "updated" in result.output
        assert patched["ttl"] == 7200

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()])

        result = invoke(["zone", "set", _zone()["id"]])
        assert result.exit_code == 0
        assert "Nothing to update" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone delete
# ══════════════════════════════════════════════════════════════════════════


class TestZoneDelete:

    def test_delete_zone(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()])

        result = invoke(["zone", "delete", _zone()["id"], "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  recordset list
# ══════════════════════════════════════════════════════════════════════════


class TestRecordList:

    def test_list_records(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()], recordsets=[
            _recordset(),
            _recordset(rs_id="rs-2", name="mail.example.com.", rtype="MX",
                       records=["10 mail.example.com."]),
        ])

        result = invoke(["recordset", "list", _zone()["id"]])
        assert result.exit_code == 0
        # Rich truncates in narrow terminals
        assert "www.exam" in result.output
        assert "mail.exa" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()], recordsets=[])

        result = invoke(["recordset", "list", _zone()["id"]])
        assert result.exit_code == 0
        assert "No recordsets found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  recordset show
# ══════════════════════════════════════════════════════════════════════════


class TestRecordShow:

    def test_show_record(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        rs = _recordset()

        def _get(url, **kwargs):
            if "/recordsets/" in url:
                return rs
            return _zone()

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.get = _get

        result = invoke(["recordset", "show", _zone()["id"], rs["id"]])
        assert result.exit_code == 0
        assert "www.example.com." in result.output


# ══════════════════════════════════════════════════════════════════════════
#  recordset create
# ══════════════════════════════════════════════════════════════════════════


class TestRecordCreate:

    def test_create_a_record(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        posted = {}

        def capture_post(url, **kwargs):
            posted.update(kwargs.get("json", {}))
            return {"id": "new-rs", "name": "www.example.com.", "type": "A"}

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.post = capture_post

        result = invoke(["recordset", "create", _zone()["id"], "www.example.com.",
                         "--type", "A", "--record", "1.2.3.4"])
        assert result.exit_code == 0
        assert "created" in result.output
        assert posted["type"] == "A"
        assert posted["records"] == ["1.2.3.4"]

    def test_create_multi_value(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        posted = {}

        def capture_post(url, **kwargs):
            posted.update(kwargs.get("json", {}))
            return {"id": "new-rs", "name": "example.com.", "type": "A"}

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.post = capture_post

        result = invoke(["recordset", "create", _zone()["id"], "example.com.",
                         "--type", "A", "--record", "1.2.3.4", "--record", "5.6.7.8"])
        assert result.exit_code == 0
        assert posted["records"] == ["1.2.3.4", "5.6.7.8"]

    def test_create_with_ttl(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        posted = {}

        def capture_post(url, **kwargs):
            posted.update(kwargs.get("json", {}))
            return {"id": "new-rs", "name": "www.example.com.", "type": "A"}

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.post = capture_post

        result = invoke(["recordset", "create", _zone()["id"], "www.example.com.",
                         "--type", "A", "--record", "1.2.3.4", "--ttl", "600"])
        assert result.exit_code == 0
        assert posted["ttl"] == 600


# ══════════════════════════════════════════════════════════════════════════
#  recordset set (formerly record-update)
# ══════════════════════════════════════════════════════════════════════════


class TestRecordUpdate:

    def test_update_record(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        put_body = {}

        def capture_put(url, **kwargs):
            put_body.update(kwargs.get("json", {}))
            return {}

        _setup_mock(mock_client, zones=[_zone()])
        mock_client.put = capture_put

        result = invoke(["recordset", "set", _zone()["id"], "rs-1",
                         "--record", "9.8.7.6", "--ttl", "120"])
        assert result.exit_code == 0
        assert "updated" in result.output
        assert put_body["records"] == ["9.8.7.6"]
        assert put_body["ttl"] == 120

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()])

        result = invoke(["recordset", "set", _zone()["id"], "rs-1"])
        assert result.exit_code == 0
        assert "Nothing to update" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  recordset delete
# ══════════════════════════════════════════════════════════════════════════


class TestRecordDelete:

    def test_delete_record(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, zones=[_zone()])

        result = invoke(["recordset", "delete", _zone()["id"], "rs-1", "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone tree
# ══════════════════════════════════════════════════════════════════════════


class TestZoneTree:

    def test_tree_display(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        z = _zone()
        rsets = [
            _recordset(rs_id="rs-1", name="example.com.", rtype="SOA",
                       records=["ns1.example.com. admin.example.com. 1 3600 600 604800 300"]),
            _recordset(rs_id="rs-2", name="example.com.", rtype="NS",
                       records=["ns1.example.com.", "ns2.example.com."]),
            _recordset(rs_id="rs-3", name="www.example.com.", rtype="A",
                       records=["1.2.3.4"]),
            _recordset(rs_id="rs-4", name="mail.example.com.", rtype="MX",
                       records=["10 mail.example.com."]),
        ]

        _ = {"n": 0}
        _ = mock_client.get

        def _get(url, **kwargs):
            if "/recordsets" in url:
                return {"recordsets": rsets, "links": {}}
            if "/v2/zones/" in url:
                return z
            return {"zones": [z]}

        _setup_mock(mock_client, zones=[z], recordsets=rsets)
        mock_client.get = _get

        result = invoke(["zone", "tree", z["id"]])
        assert result.exit_code == 0
        assert "example.com." in result.output
        assert "SOA" in result.output
        assert "NS" in result.output
        assert "A" in result.output
        assert "MX" in result.output

    def test_tree_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        z = _zone()

        def _get(url, **kwargs):
            if "/recordsets" in url:
                return {"recordsets": [], "links": {}}
            return z

        _setup_mock(mock_client, zones=[z])
        mock_client.get = _get

        result = invoke(["zone", "tree", z["id"]])
        assert result.exit_code == 0
        assert "example.com." in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone reverse-lookup
# ══════════════════════════════════════════════════════════════════════════


class TestReverseLookup:

    def test_reverse_found_via_floatingips(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        def _get(url, **kwargs):
            if "reverse/floatingips" in url:
                return {"floatingips": [
                    {"id": "fip-1", "address": "192.0.2.1", "ptrdname": "web.example.com."},
                ]}
            return {}

        _setup_mock(mock_client)
        mock_client.get = _get

        result = invoke(["zone", "reverse-lookup", "192.0.2.1"])
        assert result.exit_code == 0
        assert "web.example.com." in result.output

    def test_reverse_not_found(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        def _get(url, **kwargs):
            if "reverse/floatingips" in url:
                return {"floatingips": []}
            if "/recordsets" in url:
                return {"recordsets": []}
            return {}

        _setup_mock(mock_client)
        mock_client.get = _get

        result = invoke(["zone", "reverse-lookup", "192.0.2.99"])
        assert result.exit_code == 0
        assert "No PTR record found" in result.output

    def test_reverse_fallback_to_arpa(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        def _get(url, **kwargs):
            if "reverse/floatingips" in url:
                raise Exception("not supported")
            if "/recordsets" in url:
                return {"recordsets": [
                    {"zone_name": "2.0.192.in-addr.arpa.", "zone_id": "z-1",
                     "records": ["host.example.com."]},
                ]}
            return {}

        _setup_mock(mock_client)
        mock_client.get = _get

        result = invoke(["zone", "reverse-lookup", "192.0.2.1"])
        assert result.exit_code == 0
        assert "host.example.com." in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestDnsHelp:

    def test_zone_help(self, invoke):
        result = invoke(["zone", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete",
                    "tree", "reverse-lookup", "export", "import"):
            assert cmd in result.output

    def test_recordset_help(self, invoke):
        result = invoke(["recordset", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete"):
            assert cmd in result.output

    def test_zone_create_help(self, invoke):
        result = invoke(["zone", "create", "--help"])
        assert result.exit_code == 0
        assert "--email" in result.output

    def test_recordset_create_help(self, invoke):
        result = invoke(["recordset", "create", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--record" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  zone transfer-request / transfer-accept / tld
# ══════════════════════════════════════════════════════════════════════════

_ZONE_NAME = "example.com."
_ZONE_ID2 = "dddddddd-dddd-dddd-dddd-dddddddddddd"
_XFER_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


class TestZoneTransferRequest:

    def _req(self, **kw):
        return {"id": _XFER_ID, "zone_id": _ZONE_ID2, "zone_name": _ZONE_NAME,
                "status": "ACTIVE", "target_project_id": None, **kw}

    def test_create(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.get.side_effect = [
            {"zones": [{"id": _ZONE_ID2, "name": _ZONE_NAME}]},
        ]
        mock_client.post.return_value = {"id": _XFER_ID, "key": "secret-key"}
        result = invoke(["zone", "transfer-request-create", _ZONE_NAME])
        assert result.exit_code == 0
        assert "secret-key" in result.output

    def test_list(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.get.return_value = {"transfer_requests": [self._req()]}
        result = invoke(["zone", "transfer-request-list"])
        assert result.exit_code == 0

    def test_list_empty(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.get.return_value = {"transfer_requests": []}
        result = invoke(["zone", "transfer-request-list"])
        assert "No transfer" in result.output

    def test_show(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.get.return_value = {
            "id": _XFER_ID, "zone_id": _ZONE_ID2, "zone_name": _ZONE_NAME,
            "status": "ACTIVE", "target_project_id": "", "description": "",
            "created_at": "", "updated_at": "",
        }
        result = invoke(["zone", "transfer-request-show", _XFER_ID])
        assert result.exit_code == 0

    def test_delete_yes(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        result = invoke(["zone", "transfer-request-delete", _XFER_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        result = invoke(["zone", "transfer-request-delete", _XFER_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_accept(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.post.return_value = {"zone_id": _ZONE_ID2}
        result = invoke(["zone", "transfer-accept", _XFER_ID, "mykey"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["key"] == "mykey"
        assert body["zone_transfer_request_id"] == _XFER_ID

    def test_help_create(self, invoke):
        assert invoke(["zone", "transfer-request-create", "--help"]).exit_code == 0

    def test_help_list(self, invoke):
        assert invoke(["zone", "transfer-request-list", "--help"]).exit_code == 0

    def test_help_accept(self, invoke):
        assert invoke(["zone", "transfer-accept", "--help"]).exit_code == 0


class TestZoneTld:

    def test_list(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.get.return_value = {"tlds": [
            {"id": "1", "name": "com", "description": ""},
        ]}
        result = invoke(["zone", "tld-list"])
        assert result.exit_code == 0
        assert "com" in result.output

    def test_create(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        mock_client.post.return_value = {"id": "1", "name": "example"}
        result = invoke(["zone", "tld-create", "example"])
        assert result.exit_code == 0

    def test_delete_yes(self, invoke, mock_client):
        mock_client.dns_url = DNS_URL
        result = invoke(["zone", "tld-delete", "1", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_help_list(self, invoke):
        assert invoke(["zone", "tld-list", "--help"]).exit_code == 0

    def test_help_create(self, invoke):
        assert invoke(["zone", "tld-create", "--help"]).exit_code == 0
