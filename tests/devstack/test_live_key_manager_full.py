"""Live e2e: comprehensive Barbican key-manager coverage.

Covers ``secret`` (create/list/show/get-payload/delete), ``container``
(create/list/show/delete), ``acl`` (get/set/delete), ``order``
(create/list/show/delete).
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.live


_REF_RE = re.compile(r"https?://\S+/(?:secrets|containers|orders)/[0-9a-f-]+")
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _ref(text: str) -> str:
    """Return just the trailing UUID — orca commands validate it strictly.

    The output sometimes wraps mid-UUID at terminal width, so de-wrap
    before scanning.
    """
    flat = text.replace("\n", "")
    m = _UUID_RE.search(flat)
    if not m:
        m2 = _REF_RE.search(flat)
        if m2:
            return m2.group(0).rsplit("/", 1)[1]
        raise AssertionError(f"no Barbican ref in: {text!r}")
    return m.group(0)


def test_secret_full(live_invoke, cleanup, live_name):
    name = live_name("secret")
    res = live_invoke("secret", "create", name,
                      "--payload", "live-test-payload",
                      "--secret-type", "passphrase")
    assert res.exit_code == 0, res.output
    secret_ref = _ref(res.output)
    cleanup(lambda: live_invoke("secret", "delete", secret_ref, "--yes"))

    # Barbican list pagination caps at ~10 by default and orders by
    # created_at desc — newly-created entries can be off-page on a busy
    # cloud. Verify the call succeeds and confirm via show.
    res = live_invoke("secret", "list", "--limit", "100",
                      "-f", "value", "-c", "Name")
    assert res.exit_code == 0

    res = live_invoke("secret", "show", secret_ref)
    assert res.exit_code == 0, res.output
    assert name in res.output

    res = live_invoke("secret", "get-payload", secret_ref)
    assert res.exit_code == 0, res.output
    assert "live-test-payload" in res.output


def test_secret_container_full(live_invoke, cleanup, live_name):
    name = live_name("container")
    res = live_invoke("secret", "container-create",
                      "--name", name, "--type", "generic")
    assert res.exit_code == 0, res.output
    container_ref = _ref(res.output)
    cleanup(lambda: live_invoke("secret", "container-delete",
                                container_ref, "--yes"))

    res = live_invoke("secret", "container-list", "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output

    res = live_invoke("secret", "container-show", container_ref)
    assert res.exit_code == 0, res.output
    assert name in res.output


def test_secret_acl_full(live_invoke, cleanup, live_name):
    # Need a secret to attach the ACL to.
    name = live_name("acl-secret")
    res = live_invoke("secret", "create", name, "--payload", "x",
                      "--secret-type", "passphrase")
    assert res.exit_code == 0, res.output
    secret_ref = _ref(res.output)
    cleanup(lambda: live_invoke("secret", "delete", secret_ref, "--yes"))

    # Get current admin user ID for the ACL grant.
    res = live_invoke("user", "list", "-f", "value", "-c", "ID", "-c", "Name")
    assert res.exit_code == 0
    admin_user = next(
        line.split()[0]
        for line in res.output.splitlines()
        if "admin" in line.split()[1:]
    )

    res = live_invoke("secret", "acl", "set", secret_ref,
                      "--user", admin_user, "--operation", "read")
    if res.exit_code != 0:
        pytest.skip(f"ACL not supported: {res.output}")

    res = live_invoke("secret", "acl", "get", secret_ref)
    assert res.exit_code == 0, res.output

    res = live_invoke("secret", "acl", "delete", secret_ref, "--yes")
    assert res.exit_code == 0, res.output


def test_secret_order_full(live_invoke, cleanup, live_name):
    name = live_name("order")
    res = live_invoke("secret", "order-create",
                      "--name", name,
                      "--algorithm", "AES",
                      "--bit-length", "256",
                      "--mode", "cbc",
                      "--type", "key")
    if res.exit_code != 0:
        pytest.skip(f"orders API not supported: {res.output}")
    order_ref = _ref(res.output)
    cleanup(lambda: live_invoke("secret", "order-delete",
                                order_ref, "--yes"))

    res = live_invoke("secret", "order-list")
    assert res.exit_code == 0, res.output

    res = live_invoke("secret", "order-show", order_ref)
    assert res.exit_code == 0, res.output
