"""Shared fixtures for live e2e tests against a real OpenStack cloud.

Tests in this directory are marked ``@pytest.mark.live`` and excluded
from the default ``pytest`` run (see ``pyproject.toml``). To execute::

    pytest -m live tests/devstack/

A working orca profile named ``devstack`` (or whatever
``ORCA_LIVE_PROFILE`` points to) must exist in ``~/.orca/config.yaml``.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Callable

import pytest
from click.testing import CliRunner

from orca_cli.core.client import OrcaClient
from orca_cli.core.config import load_config
from orca_cli.main import cli

# ── Profile resolution & client ─────────────────────────────────────────


@pytest.fixture(scope="session")
def live_profile_name() -> str:
    return os.environ.get("ORCA_LIVE_PROFILE", "devstack")


@pytest.fixture(scope="session")
def live_config(live_profile_name: str) -> dict:
    try:
        return load_config(live_profile_name)
    except Exception as exc:
        pytest.skip(f"orca profile {live_profile_name!r} not loadable: {exc}")


@pytest.fixture(scope="session")
def live_client(live_config: dict) -> OrcaClient:
    """Authenticated OrcaClient against the live cloud."""
    client = OrcaClient(live_config)
    client.authenticate()
    return client


# ── CLI runner ───────────────────────────────────────────────────────────


@pytest.fixture
def live_invoke(live_profile_name: str):
    """Invoke the orca CLI in-process against the live profile.

    Returns a ``click.testing.Result`` — check ``result.exit_code`` and
    ``result.output``.
    """
    runner = CliRunner()

    def _invoke(*args: str, input: str | None = None):
        return runner.invoke(
            cli,
            ["-P", live_profile_name, *args],
            catch_exceptions=False,
            input=input,
        )

    return _invoke


# ── Cleanup tracker ──────────────────────────────────────────────────────


@pytest.fixture
def cleanup():
    """LIFO cleanup callback registry that runs even on test failure.

    Use it like::

        def test_foo(live_client, cleanup):
            res = create_something(live_client)
            cleanup(lambda: delete_something(live_client, res["id"]))
            ...

    Callbacks run in reverse-registration order during teardown, and
    failures are logged (not re-raised) so a botched cleanup doesn't
    mask the original test result.
    """
    callbacks: list[Callable[[], None]] = []

    yield callbacks.append

    for cb in reversed(callbacks):
        try:
            cb()
        except Exception as exc:  # noqa: BLE001 - cleanup must be lenient
            print(f"[live-cleanup] {cb!r} failed: {exc}")


# ── Naming helper ────────────────────────────────────────────────────────


@pytest.fixture
def live_name() -> Callable[[str], str]:
    """Return a unique, traceable resource name (prefix + short uuid).

    Lets cleanup-by-prefix work if a test crashes hard (Ctrl+C between
    creation and registration).
    """
    def _name(prefix: str) -> str:
        return f"orca-live-{prefix}-{uuid.uuid4().hex[:8]}"
    return _name


# ── Output parsing helpers ───────────────────────────────────────────────


_ID_RE = re.compile(
    # Canonical UUID (Nova/Cinder/Neutron/Glance) and bare 32-hex (Keystone).
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}",
    re.IGNORECASE,
)


def extract_uuid(text: str) -> str:
    """Pull the first resource ID out of a CLI message.

    orca's create commands print messages like ``Volume 'foo' (uuid) created.``
    rather than emitting the ID via ``-f value``, so live tests parse the ID
    out of the human-readable output. Both canonical UUIDs (Nova/Cinder/...)
    and bare 32-hex IDs (Keystone) are recognised.
    """
    match = _ID_RE.search(text)
    if not match:
        raise AssertionError(f"no resource ID found in output: {text!r}")
    return match.group(0)
