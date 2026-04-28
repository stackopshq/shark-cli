"""Live e2e: comprehensive Placement coverage.

Covers resource-class + resource-provider (CRUD + aggregate +
inventory + trait), allocation-candidate-list, allocation-show.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_resource_class_full(live_invoke, cleanup, live_name):
    rc_name = "CUSTOM_LIVE_TEST_" + live_name("rc").upper().replace("-", "_")[-12:]
    res = live_invoke("placement", "resource-class", "create", rc_name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("placement", "resource-class", "delete",
                                rc_name, "--yes"))

    res = live_invoke("placement", "resource-class", "list",
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert rc_name in res.output

    res = live_invoke("placement", "resource-class", "show", rc_name)
    assert res.exit_code == 0, res.output


def test_resource_provider_full(live_invoke, cleanup, live_name):
    name = live_name("rp")
    res = live_invoke("placement", "resource-provider", "create", name)
    assert res.exit_code == 0, res.output
    rp_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("placement", "resource-provider", "delete",
                                rp_id, "--yes"))

    res = live_invoke("placement", "resource-provider", "set", rp_id,
                      "--name", name + "-renamed")
    assert res.exit_code == 0, res.output

    res = live_invoke("placement", "resource-provider", "list",
                      "-f", "value", "-c", "UUID")
    assert res.exit_code == 0
    assert rp_id in res.output

    res = live_invoke("placement", "resource-provider", "show", rp_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0


def test_resource_provider_inventory_full(live_invoke, cleanup, live_name):
    name = live_name("rp-inv")
    res = live_invoke("placement", "resource-provider", "create", name)
    assert res.exit_code == 0, res.output
    rp_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("placement", "resource-provider", "delete",
                                rp_id, "--yes"))

    res = live_invoke("placement", "resource-provider", "inventory-set",
                      rp_id, "VCPU",
                      "--total", "16", "--reserved", "0",
                      "--max-unit", "16", "--min-unit", "1",
                      "--step-size", "1", "--allocation-ratio", "1.0")
    assert res.exit_code == 0, res.output
    # Inventory is deleted automatically when the provider is deleted —
    # no need to register a separate cleanup (which would race ordering).

    res = live_invoke("placement", "resource-provider", "inventory-list",
                      rp_id, "-f", "value", "-c", "Resource Class")
    assert res.exit_code == 0
    assert "VCPU" in res.output

    res = live_invoke("placement", "resource-provider", "inventory-show",
                      rp_id, "VCPU", "-f", "value", "-c", "total")
    assert res.exit_code == 0
    assert "16" in res.output


def test_resource_provider_trait_full(live_invoke, cleanup, live_name):
    name = live_name("rp-trait")
    res = live_invoke("placement", "resource-provider", "create", name)
    assert res.exit_code == 0, res.output
    rp_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("placement", "resource-provider", "delete",
                                rp_id, "--yes"))

    res = live_invoke("placement", "resource-provider", "trait-set",
                      rp_id, "HW_CPU_X86_AVX2")
    assert res.exit_code == 0, res.output
    # Traits are detached automatically when the provider is deleted.

    res = live_invoke("placement", "resource-provider", "trait-list",
                      rp_id, "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert "HW_CPU_X86_AVX2" in res.output


def test_resource_provider_aggregate_full(live_invoke, cleanup, live_name):
    name = live_name("rp-agg")
    res = live_invoke("placement", "resource-provider", "create", name)
    assert res.exit_code == 0, res.output
    rp_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("placement", "resource-provider", "delete",
                                rp_id, "--yes"))

    import uuid as _uuid
    agg_uuid = str(_uuid.uuid4())
    res = live_invoke("placement", "resource-provider", "aggregate-set",
                      rp_id, agg_uuid)
    assert res.exit_code == 0, res.output

    res = live_invoke("placement", "resource-provider", "aggregate-list",
                      rp_id, "-f", "value")
    assert res.exit_code == 0
    assert agg_uuid in res.output

    res = live_invoke("placement", "resource-provider", "aggregate-delete",
                      rp_id, "--yes")
    assert res.exit_code == 0, res.output


def test_allocation_candidate_list(live_invoke):
    res = live_invoke("placement", "allocation", "candidate-list",
                      "--resource", "VCPU=1")
    assert res.exit_code == 0, res.output


def test_resource_provider_usage(live_invoke):
    # Use the existing nova-compute provider
    res = live_invoke("placement", "resource-provider", "list",
                      "-f", "value", "-c", "UUID")
    assert res.exit_code == 0
    rp_id = res.output.strip().splitlines()[0]

    res = live_invoke("placement", "resource-provider", "usage", rp_id)
    assert res.exit_code == 0, res.output
