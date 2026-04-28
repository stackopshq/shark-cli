"""Live e2e: Keystone service catalogue commands.

Covers ``service``, ``endpoint``, ``endpoint-group`` and ``region`` —
22 sub-commands total.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_identity_catalog_full(live_invoke, cleanup, live_name):
    # ── REGION ────────────────────────────────────────────────────────
    region_id = live_name("region").replace("-", "_")  # region IDs prefer no dashes
    res = live_invoke("region", "create", region_id,
                      "--description", "live test region")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("region", "delete", region_id, "--yes"))

    res = live_invoke("region", "set", region_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("region", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert region_id in res.output

    res = live_invoke("region", "show", region_id,
                      "-f", "value", "-c", "description")
    assert res.exit_code == 0
    assert "updated" in res.output

    # ── SERVICE ───────────────────────────────────────────────────────
    service_name = live_name("svc")
    service_type = "live-test-" + service_name[-8:]
    res = live_invoke("service", "create",
                      "--name", service_name,
                      "--type", service_type,
                      "--description", "live test service")
    assert res.exit_code == 0, res.output
    service_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("service", "delete", service_id, "--yes"))

    res = live_invoke("service", "set", service_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("service", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert service_id in res.output

    res = live_invoke("service", "show", service_id,
                      "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert service_name in res.output

    # ── ENDPOINT ──────────────────────────────────────────────────────
    res = live_invoke("endpoint", "create",
                      "--service", service_id,
                      "--interface", "public",
                      "--url", "http://example.com/live",
                      "--region", region_id)
    assert res.exit_code == 0, res.output
    endpoint_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("endpoint", "delete", endpoint_id, "--yes"))

    res = live_invoke("endpoint", "set", endpoint_id,
                      "--url", "http://example.com/live-v2")
    assert res.exit_code == 0, res.output

    res = live_invoke("endpoint", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert endpoint_id in res.output

    res = live_invoke("endpoint", "show", endpoint_id,
                      "-f", "value", "-c", "url")
    assert res.exit_code == 0
    assert "live-v2" in res.output

    # ── ENDPOINT GROUP ────────────────────────────────────────────────
    eg_name = live_name("eg")
    res = live_invoke("endpoint-group", "create",
                      "--name", eg_name,
                      "--filter", f"service_id={service_id}",
                      "--description", "live test eg")
    assert res.exit_code == 0, res.output
    eg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("endpoint-group", "delete", eg_id, "--yes"))

    res = live_invoke("endpoint-group", "set", eg_id, "--description", "updated")
    assert res.exit_code == 0, res.output

    res = live_invoke("endpoint-group", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert eg_id in res.output

    res = live_invoke("endpoint-group", "show", eg_id,
                      "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert eg_name in res.output

    # add-project / remove-project — need a transient project
    project_name = live_name("eg-proj")
    res = live_invoke("project", "create", project_name)
    assert res.exit_code == 0, res.output
    project_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", project_id, "--yes"))

    res = live_invoke("endpoint-group", "add-project", eg_id, project_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("endpoint-group", "remove-project",
                      eg_id, project_id, "--yes")
    assert res.exit_code == 0, res.output
