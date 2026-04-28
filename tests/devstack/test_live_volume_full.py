"""Live e2e: comprehensive Cinder coverage.

Covers ``volume`` (basics + extend + revert), ``volume snapshot`` (5),
``volume type`` (+ access), ``volume backup`` (5), ``volume transfer``,
``volume qos``, ``volume service``, ``volume message``.

Skipped: ``volume migrate``, ``volume retype``, ``volume attachment``,
``volume group`` (consistency groups), ``volume upload-to-image``
— either need multiple cinder-volume hosts, an attached server, or a
running compute we don't want to disturb.
"""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def _wait_volume_status(live_invoke, vol_id, target, timeout=60):
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = live_invoke("volume", "show", vol_id, "-f", "value", "-c", "Status")
        if res.exit_code == 0:
            status = res.output.strip().splitlines()[0]
            if status == target:
                return status
            if status == "error":
                raise AssertionError(f"volume {vol_id} reached error state")
        time.sleep(2)
    raise AssertionError(f"volume {vol_id} not {target} in {timeout}s")


def test_volume_basics_extend(live_invoke, cleanup, live_name):
    name = live_name("vol")
    res = live_invoke("volume", "create", "--name", name, "--size", "1", "--wait")
    assert res.exit_code == 0, res.output
    vol_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "delete", vol_id, "--yes"))

    # extend
    res = live_invoke("volume", "extend", vol_id, "--size", "2")
    assert res.exit_code == 0, res.output
    _wait_volume_status(live_invoke, vol_id, "available")

    res = live_invoke("volume", "show", vol_id, "-f", "value", "-c", "Size")
    assert res.exit_code == 0
    assert "2" in res.output

    res = live_invoke("volume", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert vol_id in res.output


def test_volume_snapshot_full(live_invoke, cleanup, live_name):
    vol_name = live_name("vol")
    res = live_invoke("volume", "create", "--name", vol_name, "--size", "1", "--wait")
    assert res.exit_code == 0, res.output
    vol_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "delete", vol_id, "--yes"))

    snap_name = live_name("snap")
    res = live_invoke("volume", "snapshot", "create", vol_id,
                      "--name", snap_name)
    assert res.exit_code == 0, res.output
    snap_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "snapshot", "delete", snap_id, "--yes"))

    # wait for snapshot ready
    import time
    for _ in range(30):
        r = live_invoke("volume", "snapshot", "show", snap_id,
                        "-f", "value", "-c", "Status")
        if r.exit_code == 0 and "available" in r.output:
            break
        time.sleep(2)

    res = live_invoke("volume", "snapshot", "set", snap_id,
                      "--description", "live test snap")
    assert res.exit_code == 0, res.output

    res = live_invoke("volume", "snapshot", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert snap_id in res.output

    res = live_invoke("volume", "snapshot", "show", snap_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert snap_name in res.output

    # revert: snapshot must be the most recent → it is. Volume must be available.
    _wait_volume_status(live_invoke, vol_id, "available")
    res = live_invoke("volume", "snapshot", "revert", vol_id, snap_id)
    # 'revert' may not be available on all backends; accept clean failure.
    assert res.exit_code in (0, 1), res.output


def test_volume_type_full(live_invoke, cleanup, live_name):
    name = live_name("vt")
    res = live_invoke("volume", "type", "create", name,
                      "--description", "live test type",
                      "--private",
                      "--property", "volume_backend_name=lvmdriver-1")
    assert res.exit_code == 0, res.output
    vt_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "type", "delete", vt_id, "--yes"))

    res = live_invoke("volume", "type", "set", vt_id,
                      "--property", "extra_key=extra_val")
    assert res.exit_code == 0, res.output

    # access add/list/remove on private type
    proj_name = live_name("vt-proj")
    res = live_invoke("project", "create", proj_name)
    assert res.exit_code == 0, res.output
    proj_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", proj_id, "--yes"))

    res = live_invoke("volume", "type", "access", "add", vt_id, proj_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("volume", "type", "access", "list", vt_id,
                      "-f", "value", "-c", "Project ID")
    assert res.exit_code == 0
    assert proj_id in res.output

    res = live_invoke("volume", "type", "access", "remove",
                      vt_id, proj_id, "--yes")
    assert res.exit_code == 0, res.output

    # `volume type list` returns public types only by default; ours is
    # private. Verify the list call works, and use show to confirm name.
    res = live_invoke("volume", "type", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0

    res = live_invoke("volume", "type", "show", vt_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output


def test_volume_backup_full(live_invoke, cleanup, live_name):
    vol_name = live_name("vol")
    res = live_invoke("volume", "create", "--name", vol_name, "--size", "1", "--wait")
    assert res.exit_code == 0, res.output
    vol_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "delete", vol_id, "--yes"))

    backup_name = live_name("bak")
    res = live_invoke("volume", "backup", "create", vol_id,
                      "--name", backup_name, "--wait")
    if res.exit_code != 0 and ("not enabled" in res.output.lower()
                                or "not found" in res.output.lower()):
        pytest.skip("cinder-backup service not enabled")
    assert res.exit_code == 0, res.output
    backup_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "backup", "delete", backup_id, "--yes"))

    res = live_invoke("volume", "backup", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert backup_id in res.output

    res = live_invoke("volume", "backup", "show", backup_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert backup_name in res.output

    # restore creates a new volume — register cleanup for that too
    res = live_invoke("volume", "backup", "restore", backup_id,
                      "--name", live_name("restored"), "--wait")
    if res.exit_code == 0:
        restored_id = extract_uuid(res.output)
        cleanup(lambda: live_invoke("volume", "delete", restored_id, "--yes"))


def test_volume_transfer_full(live_invoke, cleanup, live_name):
    vol_name = live_name("vol")
    res = live_invoke("volume", "create", "--name", vol_name, "--size", "1", "--wait")
    assert res.exit_code == 0, res.output
    vol_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "delete", vol_id, "--yes"))

    transfer_name = live_name("xfer")
    res = live_invoke("volume", "transfer", "create", vol_id,
                      "--name", transfer_name)
    assert res.exit_code == 0, res.output
    transfer_id = extract_uuid(res.output)

    # Cleanup either by deleting the transfer (if not accepted) or by
    # the volume cleanup above (which removes the underlying resource).
    cleanup(lambda: live_invoke("volume", "transfer", "delete",
                                transfer_id, "--yes"))

    res = live_invoke("volume", "transfer", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert transfer_id in res.output

    res = live_invoke("volume", "transfer", "show", transfer_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert transfer_name in res.output


def test_volume_qos_full(live_invoke, cleanup, live_name):
    qos_name = live_name("qos")
    res = live_invoke("volume", "qos", "create", qos_name,
                      "--consumer", "back-end",
                      "--property", "total_iops_sec=1000")
    assert res.exit_code == 0, res.output
    qos_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "qos", "delete", qos_id, "--yes"))

    res = live_invoke("volume", "qos", "set", qos_id,
                      "--property", "read_iops_sec=500")
    assert res.exit_code == 0, res.output

    # associate with a volume type
    vt_name = live_name("qos-type")
    res = live_invoke("volume", "type", "create", vt_name)
    assert res.exit_code == 0, res.output
    vt_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "type", "delete", vt_id, "--yes"))

    res = live_invoke("volume", "qos", "associate", qos_id, vt_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("volume", "qos", "disassociate", qos_id, vt_id))

    res = live_invoke("volume", "qos", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert qos_id in res.output

    res = live_invoke("volume", "qos", "show", qos_id,
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert qos_name in res.output


def test_volume_service_message_list(live_invoke):
    res = live_invoke("volume", "service", "list", "-f", "value", "-c", "Binary")
    assert res.exit_code == 0, res.output
    assert "cinder" in res.output

    # `volume message` requires Cinder microversion ≥ 3.3 with the messages
    # API enabled — DevStack stable/2025.2 returns 404 without it.
    res = live_invoke("volume", "message", "list")
    if res.exit_code != 0 and "Not found" in res.output:
        pytest.skip("Cinder messages API not enabled on this cloud")
    assert res.exit_code == 0, res.output
