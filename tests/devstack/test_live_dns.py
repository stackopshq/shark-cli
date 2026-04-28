"""Live e2e: Designate DNS zones."""

from __future__ import annotations

import uuid

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_zone_create_show_delete(live_invoke, cleanup):
    # DNS zones must be FQDN ending with a dot. Generate a unique one.
    domain = f"orca-live-{uuid.uuid4().hex[:8]}.example.com."

    res = live_invoke("zone", "create", domain,
                      "--email", "admin@example.com")
    assert res.exit_code == 0, res.output
    zone_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("zone", "delete", zone_id, "--yes"))

    res = live_invoke("zone", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert zone_id in res.output

    res = live_invoke("zone", "show", zone_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert domain in res.output
