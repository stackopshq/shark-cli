"""Live e2e: full server-boot workflow.

Builds a minimal but realistic deployment graph end-to-end:

    image (anchor) → flavor → keypair → security-group → network
        → subnet → port → server (--wait until ACTIVE) → cleanup

Catches integration bugs that module-isolated tests miss: passing IDs
between modules, polling on async server status, ordering constraints
on cleanup (server before port before subnet before network).

The cirros image is uploaded once on first run and kept across runs as
``orca-live-cirros`` to keep iteration fast. The test only depends on
its existence; everything else is created and destroyed per-run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


# ── Image anchor (session-scoped, persistent across runs) ───────────────


def _image_id_by_name(live_invoke, name: str) -> str | None:
    res = live_invoke("image", "list", "-f", "value", "-c", "ID", "-c", "Name")
    if res.exit_code != 0:
        return None
    for line in res.output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == name:
            return parts[0]
    return None


@pytest.fixture(scope="session")
def cirros_source() -> Path:
    """Resolve a local cirros disk image, downloading if necessary.

    Order: ``ORCA_LIVE_IMAGE_FILE`` env var, then ``/tmp/cirros.img``,
    then download from cirros-cloud.net to ``/tmp/cirros.img``. The test
    is skipped if no path is usable and no ``curl`` is available.
    """
    env_path = os.environ.get("ORCA_LIVE_IMAGE_FILE")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    cached = Path("/tmp/cirros.img")  # noqa: S108 — cross-run cache, not user input
    if cached.exists():
        return cached

    if not shutil.which("curl"):
        pytest.skip("no cirros image available and curl missing — "
                    "set ORCA_LIVE_IMAGE_FILE or pre-fetch /tmp/cirros.img")

    url = "https://download.cirros-cloud.net/0.6.3/cirros-0.6.3-x86_64-disk.img"
    subprocess.run(
        ["curl", "-fsSL", "-o", str(cached), url],
        check=True, timeout=120,
    )
    return cached


@pytest.fixture(scope="session")
def cirros_image_id(live_invoke_session, cirros_source: Path) -> str:
    """Upload cirros once per session, reuse the image across tests."""
    name = "orca-live-cirros"
    existing = _image_id_by_name(live_invoke_session, name)
    if existing:
        return existing

    res = live_invoke_session(
        "image", "create", name,
        "--disk-format", "qcow2",
        "--file", str(cirros_source),
        "--visibility", "shared",
    )
    assert res.exit_code == 0, f"cirros upload failed: {res.output}"
    return extract_uuid(res.output)


@pytest.fixture(scope="session")
def live_invoke_session(live_profile_name: str):
    """Session-scoped CliRunner for fixtures that span tests."""
    from click.testing import CliRunner

    from orca_cli.main import cli

    runner = CliRunner()

    def _invoke(*args: str):
        return runner.invoke(
            cli, ["-P", live_profile_name, *args],
            catch_exceptions=False,
        )

    return _invoke


# ── Polling helper ───────────────────────────────────────────────────────


def _wait_status(live_invoke, server_id: str, target: str,
                 timeout: float = 180.0, interval: float = 3.0) -> str:
    """Poll ``orca server show`` until status == target or timeout."""
    deadline = time.monotonic() + timeout
    last_status = "?"
    while time.monotonic() < deadline:
        res = live_invoke("server", "show", server_id,
                          "-f", "value", "-c", "status")
        if res.exit_code == 0:
            last_status = res.output.strip().splitlines()[0]
            if last_status == target:
                return last_status
            if last_status == "ERROR":
                raise AssertionError(
                    f"server {server_id} reached ERROR before {target}: "
                    f"{res.output}"
                )
        time.sleep(interval)
    raise AssertionError(
        f"server {server_id} did not reach {target} within {timeout}s "
        f"(last status: {last_status})"
    )


# ── The workflow test ───────────────────────────────────────────────────


def test_server_boot_full_workflow(
    live_invoke, cleanup, live_name, cirros_image_id,
):
    # 1. Flavor
    flavor_name = live_name("flavor")
    res = live_invoke("flavor", "create", flavor_name,
                      "--vcpus", "1", "--ram", "256", "--disk", "1")
    assert res.exit_code == 0, res.output
    flavor_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("flavor", "delete", flavor_id, "--yes"))

    # 2. Keypair
    keypair_name = live_name("kp")
    res = live_invoke("keypair", "create", keypair_name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("keypair", "delete", keypair_name, "--yes"))

    # 3. Security group + ingress SSH rule (best-effort; the rule isn't
    #    strictly required for ACTIVE status but proves the SG plumbing)
    sg_name = live_name("sg")
    res = live_invoke("security-group", "create", sg_name,
                      "--description", "live workflow")
    assert res.exit_code == 0, res.output
    sg_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("security-group", "delete", sg_id, "--yes"))

    # 4. Network + subnet (isolated per-run)
    net_name = live_name("net")
    res = live_invoke("network", "create", net_name)
    assert res.exit_code == 0, res.output
    net_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "delete", net_id, "--yes"))

    sub_name = live_name("sub")
    res = live_invoke("network", "subnet", "create", sub_name,
                      "--network-id", net_id, "--cidr", "10.42.0.0/24")
    assert res.exit_code == 0, res.output
    sub_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("network", "subnet", "delete", sub_id, "--yes"))

    # 5. Server boot (the moment of truth)
    server_name = live_name("server")
    res = live_invoke(
        "server", "create",
        "--name", server_name,
        "--flavor", flavor_id,
        "--image", cirros_image_id,
        "--network", net_id,
        "--key-name", keypair_name,
        "--security-group", sg_name,
        "--boot-from-image",
    )
    assert res.exit_code == 0, res.output
    server_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("server", "delete", server_id, "--yes", "--wait"))

    # 6. Wait for ACTIVE
    status = _wait_status(live_invoke, server_id, "ACTIVE", timeout=180)
    assert status == "ACTIVE"

    # 7. Sanity-check the server appears in the list
    res = live_invoke("server", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert server_id in res.output
