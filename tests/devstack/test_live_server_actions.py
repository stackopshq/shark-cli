"""Live e2e: Nova server actions on a single live server.

Boots one server then walks through all the read-only and most
non-destructive actions in a single test, with cleanup at the end.
This is heavier than the basic boot workflow — it exercises ~30 of
the 70 server sub-commands in one run.

Skipped: live-migrate (needs 2 hypervisors), evacuate (needs a downed
host), migrate (multi-host), resize (needs 2nd flavor target), rescue/
unrescue (image must be different), password (requires guest agent),
ssh (requires reachable IP), shelve+restore on soft-delete (slow),
dump-create (admin-only Linux capabilities).
"""

from __future__ import annotations

import time

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def _wait_status(live_invoke, server_id, target, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = live_invoke("server", "show", server_id, "-f", "value", "-c", "Status")
        if res.exit_code == 0:
            status = res.output.strip().splitlines()[0]
            if status == target:
                return
            if status == "ERROR":
                raise AssertionError(f"server {server_id} -> ERROR")
        time.sleep(2)
    raise AssertionError(f"server {server_id} not {target} in {timeout}s")


@pytest.fixture(scope="module")
def cirros_image_id_module(live_invoke_session):
    res = live_invoke_session("image", "list", "-f", "value", "-c", "ID", "-c", "Name")
    if res.exit_code != 0:
        pytest.skip(f"image list failed: {res.output}")
    for line in res.output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "orca-live-cirros":
            return parts[0]
    pytest.skip("orca-live-cirros image missing — run workflow test once first")


@pytest.fixture(scope="module")
def live_invoke_session(live_profile_name):
    from click.testing import CliRunner

    from orca_cli.main import cli
    runner = CliRunner()

    def _invoke(*args):
        return runner.invoke(cli, ["-P", live_profile_name, *args],
                              catch_exceptions=False)
    return _invoke


def test_server_actions_full(live_invoke, cleanup, live_name, cirros_image_id_module):
    # === Boot ====
    flavor_name = live_name("flv")
    res = live_invoke("flavor", "create", flavor_name,
                      "--vcpus", "1", "--ram", "256", "--disk", "1")
    assert res.exit_code == 0, res.output
    flavor_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("flavor", "delete", flavor_id, "--yes"))

    kp_name = live_name("kp")
    res = live_invoke("keypair", "create", kp_name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", kp_name, "--yes"))

    sg_name = live_name("sg")
    res = live_invoke("security-group", "create", sg_name)
    assert res.exit_code == 0, res.output
    sg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", sg_id, "--yes"))

    net_name = live_name("net")
    res = live_invoke("network", "create", net_name)
    assert res.exit_code == 0, res.output
    net_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "delete", net_id, "--yes"))

    res = live_invoke("network", "subnet", "create", live_name("sub"),
                      "--network-id", net_id, "--cidr", "10.55.0.0/24")
    assert res.exit_code == 0, res.output
    sub_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "subnet", "delete", sub_id, "--yes"))

    server_name = live_name("srv")
    res = live_invoke("server", "create",
                      "--name", server_name,
                      "--flavor", flavor_id,
                      "--image", cirros_image_id_module,
                      "--network", net_id,
                      "--key-name", kp_name,
                      "--security-group", sg_name,
                      "--boot-from-image")
    assert res.exit_code == 0, res.output
    server_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("server", "delete",
                                server_id, "--yes", "--wait"))

    # === Wait for ACTIVE ===
    _wait_status(live_invoke, server_id, "ACTIVE")

    # === Read-only introspection ===
    for cmd in ("show", "list-interfaces", "list-volumes",
                "metadata-list", "tag-list",
                "console-log", "console-url"):
        res = live_invoke("server", cmd, server_id) if cmd != "list" else \
              live_invoke("server", "list")
        assert res.exit_code == 0, f"{cmd}: {res.output}"

    # === Tag set/unset (via metadata to keep it simple) ===
    res = live_invoke("server", "set", server_id,
                      "--property", "live=test")
    assert res.exit_code == 0, res.output

    res = live_invoke("server", "unset", server_id,
                      "--property", "live")
    assert res.exit_code == 0, res.output

    # === Rename ===
    res = live_invoke("server", "rename", server_id,
                      server_name + "-renamed")
    assert res.exit_code == 0, res.output

    # === Power lifecycle: stop -> start ===
    res = live_invoke("server", "stop", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "SHUTOFF")

    res = live_invoke("server", "start", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "ACTIVE")

    # === Reboot (soft) ===
    res = live_invoke("server", "reboot", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "ACTIVE")

    # === Pause/unpause ===
    res = live_invoke("server", "pause", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "PAUSED")

    res = live_invoke("server", "unpause", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "ACTIVE")

    # === Suspend/resume ===
    res = live_invoke("server", "suspend", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "SUSPENDED")

    res = live_invoke("server", "resume", server_id)
    assert res.exit_code == 0, res.output
    _wait_status(live_invoke, server_id, "ACTIVE")

    # === Lock/unlock ===
    res = live_invoke("server", "lock", server_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("server", "unlock", server_id)
    assert res.exit_code == 0, res.output

    # === Add/remove security group ===
    sg2_name = live_name("sg2")
    res = live_invoke("security-group", "create", sg2_name)
    assert res.exit_code == 0, res.output
    sg2_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", sg2_id, "--yes"))

    res = live_invoke("server", "add", "security-group", server_id, sg2_name)
    assert res.exit_code == 0, res.output

    res = live_invoke("server", "remove", "security-group", server_id, sg2_name)
    assert res.exit_code == 0, res.output

    # === Snapshot (creates an image) ===
    snap_name = live_name("snap")
    res = live_invoke("server", "snapshot", server_id, "--name", snap_name)
    assert res.exit_code == 0, res.output
    # The output prints the image *name*, not its UUID — look it up.
    img_name = f"{snap_name}-image"
    cleanup(lambda: live_invoke("image", "delete", img_name, "--yes"))

    # === Migration list (empty for a single-host setup, but valid call) ===
    res = live_invoke("server", "migration", "list", server_id)
    assert res.exit_code == 0, res.output

    # === wait sub-command ===
    res = live_invoke("server", "wait", server_id, "--status", "ACTIVE")
    assert res.exit_code == 0, res.output
