"""Unit tests for ``orca_cli.services.dns.DnsService``.

Live e2e against Designate is covered by
``tests/devstack/test_live_dns_full.py``; this suite locks the URL
and body shapes at unit-test speed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.core.exceptions import APIError
from orca_cli.services.dns import DnsService

DESIGNATE = "https://dns.example.com"
BASE = f"{DESIGNATE}/v2"  # ``with_version()`` appends v2

@pytest.fixture
def dns_client():
    client = MagicMock()
    client.dns_url = DESIGNATE
    return client

@pytest.fixture
def svc(dns_client):
    return DnsService(dns_client)

# ── zones ──────────────────────────────────────────────────────────────

def test_find_zones(dns_client, svc):
    dns_client.get.return_value = {"zones": [{"id": "z1"}]}
    out = svc.find_zones()
    dns_client.get.assert_called_once_with(f"{BASE}/zones")
    assert out[0]["id"] == "z1"

def test_find_zones_passes_params_and_headers(dns_client, svc):
    dns_client.get.return_value = {"zones": []}
    svc.find_zones(params={"name": "x"}, headers={"X-Auth-All-Projects": "true"})
    dns_client.get.assert_called_once_with(
        f"{BASE}/zones",
        params={"name": "x"},
        headers={"X-Auth-All-Projects": "true"},
    )

def test_get_zone_unwraps_envelope(dns_client, svc):
    dns_client.get.return_value = {"zone": {"id": "z1", "name": "ex.com."}}
    out = svc.get_zone("z1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/z1")
    assert out["name"] == "ex.com."

def test_get_zone_falls_back_when_no_envelope(dns_client, svc):
    dns_client.get.return_value = {"id": "raw"}
    assert svc.get_zone("z1") == {"id": "raw"}

def test_create_zone(dns_client, svc):
    dns_client.post.return_value = {"zone": {"id": "z-new"}}
    out = svc.create_zone({"name": "ex.com.", "email": "a@b"})
    dns_client.post.assert_called_once_with(
        f"{BASE}/zones", json={"name": "ex.com.", "email": "a@b"}
    )
    assert out["id"] == "z-new"

def test_create_zone_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_zone({"name": "ex.com."}) == {}

def test_update_zone_uses_patch(dns_client, svc):
    dns_client.patch.return_value = {"zone": {"id": "z1", "ttl": 600}}
    out = svc.update_zone("z1", {"ttl": 600})
    dns_client.patch.assert_called_once_with(f"{BASE}/zones/z1", json={"ttl": 600})
    assert out["ttl"] == 600

def test_update_zone_handles_none(dns_client, svc):
    dns_client.patch.return_value = None
    assert svc.update_zone("z1", {}) == {}

def test_delete_zone(dns_client, svc):
    svc.delete_zone("z1")
    dns_client.delete.assert_called_once_with(f"{BASE}/zones/z1")

# ── recordsets ─────────────────────────────────────────────────────────

def test_find_recordsets(dns_client, svc):
    dns_client.get.return_value = {"recordsets": [{"id": "r1"}]}
    svc.find_recordsets("z1", params={"type": "A"})
    dns_client.get.assert_called_once_with(
        f"{BASE}/zones/z1/recordsets", params={"type": "A"}
    )

def test_find_all_recordsets(dns_client, svc):
    dns_client.get.return_value = {"recordsets": [{"id": "r"}]}
    out = svc.find_all_recordsets(params={"name": "x.ex.com."})
    dns_client.get.assert_called_once_with(
        f"{BASE}/recordsets", params={"name": "x.ex.com."}
    )
    assert out[0]["id"] == "r"

def test_get_recordset(dns_client, svc):
    dns_client.get.return_value = {"recordset": {"id": "r1"}}
    out = svc.get_recordset("z1", "r1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/z1/recordsets/r1")
    assert out["id"] == "r1"

def test_create_recordset(dns_client, svc):
    dns_client.post.return_value = {"recordset": {"id": "r1"}}
    out = svc.create_recordset("z1", {"name": "x.ex.com.", "type": "A"})
    dns_client.post.assert_called_once_with(
        f"{BASE}/zones/z1/recordsets",
        json={"name": "x.ex.com.", "type": "A"},
    )
    assert out["id"] == "r1"

def test_create_recordset_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_recordset("z1", {}) == {}

def test_update_recordset_uses_put(dns_client, svc):
    dns_client.put.return_value = {"recordset": {"id": "r1", "ttl": 60}}
    out = svc.update_recordset("z1", "r1", {"ttl": 60})
    dns_client.put.assert_called_once_with(
        f"{BASE}/zones/z1/recordsets/r1", json={"ttl": 60}
    )
    assert out["ttl"] == 60

def test_update_recordset_handles_none(dns_client, svc):
    dns_client.put.return_value = None
    assert svc.update_recordset("z1", "r1", {}) == {}

def test_delete_recordset(dns_client, svc):
    svc.delete_recordset("z1", "r1")
    dns_client.delete.assert_called_once_with(f"{BASE}/zones/z1/recordsets/r1")

# ── export / import ───────────────────────────────────────────────────

def test_export_zone(dns_client, svc):
    dns_client.post.return_value = {"id": "exp1", "status": "PENDING"}
    out = svc.export_zone("z1")
    dns_client.post.assert_called_once_with(f"{BASE}/zones/z1/tasks/export")
    assert out["status"] == "PENDING"

def test_export_zone_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.export_zone("z1") == {}

def test_get_export_task(dns_client, svc):
    dns_client.get.return_value = {"id": "exp1", "status": "COMPLETE"}
    svc.get_export_task("exp1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/tasks/exports/exp1")

def test_get_export_task_handles_none(dns_client, svc):
    dns_client.get.return_value = None
    assert svc.get_export_task("exp1") == {}

def test_fetch_export_text_returns_body(dns_client, svc):
    resp = MagicMock(status_code=200, text="$ORIGIN ex.com.\n")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    dns_client.get_stream = MagicMock(return_value=cm)

    out = svc.fetch_export_text("exp1")
    dns_client.get_stream.assert_called_once_with(
        f"{BASE}/zones/tasks/exports/exp1/export",
        extra_headers={"Accept": "text/dns"},
    )
    assert "ex.com" in out

def test_fetch_export_text_raises_apierror_on_failure(dns_client, svc):
    resp = MagicMock(status_code=500, text="boom")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    dns_client.get_stream = MagicMock(return_value=cm)

    with pytest.raises(APIError):
        svc.fetch_export_text("exp1")

def test_import_zone_text_posts_with_text_dns(dns_client, svc):
    resp = MagicMock(status_code=202)
    resp.json.return_value = {"id": "imp1", "status": "PENDING"}
    dns_client.post_stream = MagicMock(return_value=resp)

    out = svc.import_zone_text("$ORIGIN ex.com.\n@ IN A 1.2.3.4")
    dns_client.post_stream.assert_called_once()
    args, kwargs = dns_client.post_stream.call_args
    assert args[0] == f"{BASE}/zones/tasks/imports"
    assert kwargs["content_type"] == "text/dns"
    assert kwargs["content"].startswith(b"$ORIGIN")
    assert out["id"] == "imp1"

def test_import_zone_text_accepts_bytes(dns_client, svc):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "imp1"}
    dns_client.post_stream = MagicMock(return_value=resp)
    svc.import_zone_text(b"already-bytes")
    args, kwargs = dns_client.post_stream.call_args
    assert kwargs["content"] == b"already-bytes"

def test_import_zone_text_raises_on_bad_status(dns_client, svc):
    resp = MagicMock(status_code=400, text="bad zone")
    dns_client.post_stream = MagicMock(return_value=resp)
    with pytest.raises(APIError):
        svc.import_zone_text("garbage")

def test_import_zone_text_handles_invalid_json_body(dns_client, svc):
    resp = MagicMock(status_code=202)
    resp.json.side_effect = ValueError
    dns_client.post_stream = MagicMock(return_value=resp)
    assert svc.import_zone_text("...") == {}

def test_get_import_task(dns_client, svc):
    dns_client.get.return_value = {"id": "imp1", "status": "PENDING"}
    svc.get_import_task("imp1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/tasks/imports/imp1")

def test_get_import_task_handles_none(dns_client, svc):
    dns_client.get.return_value = None
    assert svc.get_import_task("imp1") == {}

# ── transfer requests ─────────────────────────────────────────────────

def test_create_transfer_request(dns_client, svc):
    dns_client.post.return_value = {"transfer_request": {"id": "tr1", "key": "ABC"}}
    out = svc.create_transfer_request("z1", {"target_project_id": "p2"})
    dns_client.post.assert_called_once_with(
        f"{BASE}/zones/z1/tasks/transfer_requests",
        json={"target_project_id": "p2"},
    )
    assert out["key"] == "ABC"

def test_create_transfer_request_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_transfer_request("z1", {}) == {}

def test_find_transfer_requests(dns_client, svc):
    dns_client.get.return_value = {"transfer_requests": [{"id": "tr1"}]}
    out = svc.find_transfer_requests()
    dns_client.get.assert_called_once_with(f"{BASE}/zones/tasks/transfer_requests")
    assert out[0]["id"] == "tr1"

def test_get_transfer_request(dns_client, svc):
    dns_client.get.return_value = {"transfer_request": {"id": "tr1"}}
    svc.get_transfer_request("tr1")
    dns_client.get.assert_called_once_with(
        f"{BASE}/zones/tasks/transfer_requests/tr1"
    )

def test_delete_transfer_request(dns_client, svc):
    svc.delete_transfer_request("tr1")
    dns_client.delete.assert_called_once_with(
        f"{BASE}/zones/tasks/transfer_requests/tr1"
    )

def test_accept_transfer(dns_client, svc):
    dns_client.post.return_value = {"id": "ta1"}
    svc.accept_transfer({"key": "ABC", "zone_transfer_request_id": "tr1"})
    dns_client.post.assert_called_once_with(
        f"{BASE}/zones/tasks/transfer_accepts",
        json={"key": "ABC", "zone_transfer_request_id": "tr1"},
    )

def test_accept_transfer_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.accept_transfer({}) == {}

# ── reverse / TLDs / abandon / axfr ───────────────────────────────────

def test_find_reverse_floatingips(dns_client, svc):
    dns_client.get.return_value = {"floatingips": [{"id": "fip1"}]}
    out = svc.find_reverse_floatingips()
    dns_client.get.assert_called_once_with(f"{BASE}/reverse/floatingips")
    assert out[0]["id"] == "fip1"

def test_find_tlds(dns_client, svc):
    dns_client.get.return_value = {"tlds": [{"id": "t1", "name": "com"}]}
    svc.find_tlds()
    dns_client.get.assert_called_once_with(f"{BASE}/tlds")

def test_create_tld(dns_client, svc):
    dns_client.post.return_value = {"tld": {"id": "t1"}}
    out = svc.create_tld({"name": "test"})
    dns_client.post.assert_called_once_with(f"{BASE}/tlds", json={"name": "test"})
    assert out["id"] == "t1"

def test_create_tld_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_tld({}) == {}

def test_delete_tld(dns_client, svc):
    svc.delete_tld("t1")
    dns_client.delete.assert_called_once_with(f"{BASE}/tlds/t1")

def test_abandon_zone(dns_client, svc):
    svc.abandon_zone("z1")
    dns_client.post.assert_called_once_with(f"{BASE}/zones/z1/tasks/abandon")

def test_axfr_zone(dns_client, svc):
    svc.axfr_zone("z1")
    dns_client.post.assert_called_once_with(f"{BASE}/zones/z1/tasks/xfr")

# ── shares ────────────────────────────────────────────────────────────

def test_find_shares(dns_client, svc):
    dns_client.get.return_value = {"shared_zones": [{"id": "sh1"}]}
    out = svc.find_shares("z1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/z1/shares")
    assert out[0]["id"] == "sh1"

def test_get_share(dns_client, svc):
    dns_client.get.return_value = {"shared_zone": {"id": "sh1"}}
    out = svc.get_share("z1", "sh1")
    dns_client.get.assert_called_once_with(f"{BASE}/zones/z1/shares/sh1")
    assert out["id"] == "sh1"

def test_get_share_handles_unexpected(dns_client, svc):
    dns_client.get.return_value = None
    assert svc.get_share("z1", "sh1") == {}

def test_create_share(dns_client, svc):
    dns_client.post.return_value = {"shared_zone": {"id": "sh1"}}
    out = svc.create_share("z1", "target-project")
    dns_client.post.assert_called_once_with(
        f"{BASE}/zones/z1/shares",
        json={"target_project_id": "target-project"},
    )
    assert out["id"] == "sh1"

def test_create_share_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_share("z1", "p2") == {}

def test_delete_share(dns_client, svc):
    svc.delete_share("z1", "sh1")
    dns_client.delete.assert_called_once_with(f"{BASE}/zones/z1/shares/sh1")

# ── blacklists ───────────────────────────────────────────────────────

def test_find_blacklists(dns_client, svc):
    dns_client.get.return_value = {"blacklists": [{"id": "bl1"}]}
    svc.find_blacklists()
    dns_client.get.assert_called_once_with(f"{BASE}/blacklists")

def test_get_blacklist(dns_client, svc):
    dns_client.get.return_value = {"blacklist": {"id": "bl1"}}
    out = svc.get_blacklist("bl1")
    dns_client.get.assert_called_once_with(f"{BASE}/blacklists/bl1")
    assert out["id"] == "bl1"

def test_get_blacklist_handles_unexpected(dns_client, svc):
    dns_client.get.return_value = None
    assert svc.get_blacklist("bl1") == {}

def test_create_blacklist(dns_client, svc):
    dns_client.post.return_value = {"blacklist": {"id": "bl1"}}
    out = svc.create_blacklist({"pattern": ".*\\.bad\\.com\\."})
    dns_client.post.assert_called_once_with(
        f"{BASE}/blacklists", json={"pattern": ".*\\.bad\\.com\\."}
    )
    assert out["id"] == "bl1"

def test_create_blacklist_handles_none(dns_client, svc):
    dns_client.post.return_value = None
    assert svc.create_blacklist({}) == {}

def test_update_blacklist(dns_client, svc):
    dns_client.patch.return_value = {"blacklist": {"id": "bl1"}}
    out = svc.update_blacklist("bl1", {"description": "new"})
    dns_client.patch.assert_called_once_with(
        f"{BASE}/blacklists/bl1", json={"description": "new"}
    )
    assert out["id"] == "bl1"

def test_update_blacklist_handles_none(dns_client, svc):
    dns_client.patch.return_value = None
    assert svc.update_blacklist("bl1", {}) == {}

def test_delete_blacklist(dns_client, svc):
    svc.delete_blacklist("bl1")
    dns_client.delete.assert_called_once_with(f"{BASE}/blacklists/bl1")

# ── exports / imports listings ────────────────────────────────────────

def test_find_exports(dns_client, svc):
    dns_client.get.return_value = {"exports": [{"id": "e1"}]}
    out = svc.find_exports()
    dns_client.get.assert_called_once_with(f"{BASE}/zones/tasks/exports")
    assert out[0]["id"] == "e1"

def test_delete_export(dns_client, svc):
    svc.delete_export("e1")
    dns_client.delete.assert_called_once_with(f"{BASE}/zones/tasks/exports/e1")

def test_find_imports(dns_client, svc):
    dns_client.get.return_value = {"imports": [{"id": "i1"}]}
    out = svc.find_imports()
    dns_client.get.assert_called_once_with(f"{BASE}/zones/tasks/imports")
    assert out[0]["id"] == "i1"

def test_delete_import(dns_client, svc):
    svc.delete_import("i1")
    dns_client.delete.assert_called_once_with(f"{BASE}/zones/tasks/imports/i1")
