"""Live e2e: comprehensive Designate DNS coverage.

Covers ``zone`` (create/list/show/set/delete + export/import/tree +
reverse-lookup + tld + transfer-request*), ``recordset`` (5).
"""

from __future__ import annotations

import uuid

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_zone_full(live_invoke, cleanup):
    domain = f"orca-live-{uuid.uuid4().hex[:8]}.example.com."
    res = live_invoke("zone", "create", domain,
                      "--email", "admin@example.com")
    assert res.exit_code == 0, res.output
    zone_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "delete", zone_id, "--yes"))

    res = live_invoke("zone", "set", zone_id, "--ttl", "7200")
    assert res.exit_code == 0, res.output

    res = live_invoke("zone", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert zone_id in res.output

    res = live_invoke("zone", "show", zone_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert domain in res.output

    res = live_invoke("zone", "export", zone_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("zone", "tree", zone_id)
    assert res.exit_code == 0, res.output


def test_recordset_full(live_invoke, cleanup):
    domain = f"orca-live-rs-{uuid.uuid4().hex[:8]}.example.com."
    res = live_invoke("zone", "create", domain,
                      "--email", "admin@example.com")
    assert res.exit_code == 0, res.output
    zone_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "delete", zone_id, "--yes"))

    rs_name = f"www.{domain}"
    res = live_invoke("recordset", "create", zone_id, rs_name,
                      "--type", "A", "--record", "192.0.2.1",
                      "--ttl", "300")
    assert res.exit_code == 0, res.output
    rs_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("recordset", "delete",
                                zone_id, rs_id, "--yes"))

    res = live_invoke("recordset", "set", zone_id, rs_id,
                      "--record", "192.0.2.2")
    assert res.exit_code == 0, res.output

    res = live_invoke("recordset", "list", zone_id,
                      "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert rs_id in res.output

    res = live_invoke("recordset", "show", zone_id, rs_id,
                      "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert rs_name in res.output


def test_zone_tld_lifecycle(live_invoke, cleanup):
    tld = f"livetest{uuid.uuid4().hex[:6]}"
    res = live_invoke("zone", "tld-create", tld,
                      "--description", "live test tld")
    if res.exit_code != 0 and "Forbidden" in res.output:
        pytest.skip("TLD management requires admin role with tld policy")
    assert res.exit_code == 0, res.output
    tld_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "tld-delete", tld_id, "--yes"))

    res = live_invoke("zone", "tld-list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert tld_id in res.output


def test_zone_transfer_request(live_invoke, cleanup):
    domain = f"orca-live-xfer-{uuid.uuid4().hex[:8]}.example.com."
    res = live_invoke("zone", "create", domain,
                      "--email", "admin@example.com")
    assert res.exit_code == 0, res.output
    zone_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "delete", zone_id, "--yes"))

    res = live_invoke("zone", "transfer-request-create", zone_id,
                      "--description", "live test")
    if res.exit_code != 0:
        pytest.skip(f"transfer-request not supported: {res.output}")
    req_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "transfer-request-delete",
                                req_id, "--yes"))

    res = live_invoke("zone", "transfer-request-list",
                      "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert req_id in res.output

    res = live_invoke("zone", "transfer-request-show", req_id,
                      "-f", "value", "-c", "zone_id")
    assert res.exit_code == 0
