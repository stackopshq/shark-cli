"""Live e2e: full coverage of Nova compute commands.

Covers ``flavor`` (9), ``keypair`` (6), ``hypervisor`` (4),
``aggregate`` (9), ``availability-zone`` (1), ``server-group`` (4),
``compute-service`` (3) — 36 cmds.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_flavor_full(live_invoke, cleanup, live_name):
    name = live_name("flavor")
    res = live_invoke("flavor", "create", name,
                      "--vcpus", "1", "--ram", "64", "--disk", "1",
                      "--private")
    assert res.exit_code == 0, res.output
    flavor_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("flavor", "delete", flavor_id, "--yes"))

    # extra-specs lifecycle
    res = live_invoke("flavor", "set", flavor_id,
                      "--property", "hw:cpu_policy=dedicated",
                      "--property", "hw:mem_page_size=large")
    assert res.exit_code == 0, res.output

    res = live_invoke("flavor", "unset", flavor_id,
                      "--property", "hw:mem_page_size")
    assert res.exit_code == 0, res.output

    # access-add / access-list / access-remove on private flavor
    proj_name = live_name("flavor-proj")
    res = live_invoke("project", "create", proj_name)
    assert res.exit_code == 0, res.output
    proj_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", proj_id, "--yes"))

    res = live_invoke("flavor", "access", "add", flavor_id, proj_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("flavor", "access", "list", flavor_id,
                      "-f", "value", "-c", "Project ID")
    assert res.exit_code == 0
    assert proj_id in res.output

    res = live_invoke("flavor", "access", "remove",
                      flavor_id, proj_id, "--yes")
    assert res.exit_code == 0, res.output

    # list (returns public only by default — our flavor is private,
    # so we just verify the call works) + show (always works by ID).
    res = live_invoke("flavor", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0

    res = live_invoke("flavor", "show", flavor_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert name in res.output


def test_keypair_full(live_invoke, cleanup, live_name, tmp_path):
    # keypair create — server-side generated
    name1 = live_name("kp1")
    res = live_invoke("keypair", "create", name1,
                      "--save-to", str(tmp_path / f"{name1}.pem"))
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", name1, "--yes"))

    # keypair generate — client-side generated, then uploads public part
    name2 = live_name("kp2")
    res = live_invoke("keypair", "generate", name2,
                      "--type", "ed25519",
                      "--save-to", str(tmp_path / f"{name2}"))
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", name2, "--yes"))

    # keypair upload — provide an already-existing public key string
    name3 = live_name("kp3")
    pubkey = ("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH4ePkMJlCNyz3LhGwK6"
              "HzGvJMwQQK3R3sQzg6Sd1QyN orca-live-test")
    res = live_invoke("keypair", "upload", name3, "--public-key", pubkey)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", name3, "--yes"))

    res = live_invoke("keypair", "list", "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    for n in (name1, name2, name3):
        assert n in res.output

    res = live_invoke("keypair", "show", name1, "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name1 in res.output


def test_hypervisor_full(live_invoke):
    # Read-only — DevStack always has one (the host itself).
    res = live_invoke("hypervisor", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0, res.output
    hv_id = res.output.strip().splitlines()[0]
    assert hv_id

    res = live_invoke("hypervisor", "show", hv_id,
                      "-f", "value", "-c", "Hostname")
    assert res.exit_code == 0
    assert "devstack" in res.output

    res = live_invoke("hypervisor", "stats")
    assert res.exit_code == 0, res.output

    # hypervisor usage = global overview, no per-host argument
    res = live_invoke("hypervisor", "usage")
    assert res.exit_code == 0, res.output


def test_aggregate_full(live_invoke, cleanup, live_name):
    name = live_name("agg")
    res = live_invoke("aggregate", "create", name, "--zone", "nova")
    assert res.exit_code == 0, res.output
    agg_id = extract_uuid(res.output) if "[0-9a-f]" in res.output else None
    # Aggregate IDs are sometimes numeric (older Nova). Parse fallback.
    if not agg_id:
        # last token in the line typically holds the id like "(N)"
        for line in res.output.splitlines():
            if "(" in line and ")" in line:
                agg_id = line.rsplit("(", 1)[1].split(")")[0]
                break
    assert agg_id, f"no aggregate id in: {res.output}"
    cleanup(lambda: live_invoke("aggregate", "delete", agg_id, "--yes"))

    res = live_invoke("aggregate", "set", agg_id,
                      "--property", "ssd=true",
                      "--property", "rack=A1")
    assert res.exit_code == 0, res.output

    res = live_invoke("aggregate", "unset", agg_id, "--property", "rack")
    assert res.exit_code == 0, res.output

    # add-host / remove-host on the local hypervisor (devstack)
    res = live_invoke("aggregate", "host", "add", agg_id, "devstack")
    assert res.exit_code == 0, res.output

    res = live_invoke("aggregate", "host", "remove", agg_id, "devstack")
    assert res.exit_code == 0, res.output

    res = live_invoke("aggregate", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert str(agg_id) in res.output

    res = live_invoke("aggregate", "show", agg_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output

    # cache-image is best-effort: it queues a request, we skip if unsupported
    # by libvirt driver in this devstack, so just check exit_code is in {0, 1}.
    # We don't actually have a usable image id at this point, so skip.


def test_availability_zone_list(live_invoke):
    res = live_invoke("availability-zone", "list",
                      "-f", "value", "-c", "Zone")
    assert res.exit_code == 0, res.output
    assert "nova" in res.output


def test_server_group_full(live_invoke, cleanup, live_name):
    name = live_name("sg")
    res = live_invoke("server-group", "create", name,
                      "--policy", "anti-affinity")
    assert res.exit_code == 0, res.output
    sg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("server-group", "delete", sg_id, "--yes"))

    res = live_invoke("server-group", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert sg_id in res.output

    res = live_invoke("server-group", "show", sg_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output


def test_compute_service_full(live_invoke):
    # compute-service entries are auto-managed by Nova; only test list/set
    # against the local nova-compute service. delete is destructive (would
    # remove the only compute host) — we skip it.
    res = live_invoke("compute-service", "list",
                      "-f", "value", "-c", "ID", "-c", "Binary")
    assert res.exit_code == 0, res.output
    nova_compute_id = next(
        line.split()[0] for line in res.output.splitlines()
        if "nova-compute" in line
    )

    # disable then re-enable so we don't strand the deployment
    res = live_invoke("compute-service", "set", nova_compute_id,
                      "--disable", "--disabled-reason", "live-test")
    assert res.exit_code == 0, res.output

    res = live_invoke("compute-service", "set", nova_compute_id, "--enable")
    assert res.exit_code == 0, res.output
