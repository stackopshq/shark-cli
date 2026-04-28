"""Live e2e: Barbican secrets."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_secret_create_list_delete(live_invoke, cleanup, live_name):
    name = live_name("secret")

    res = live_invoke("secret", "create", name,
                      "--payload", "live-test-payload",
                      "--secret-type", "passphrase")
    assert res.exit_code == 0, res.output

    # Barbican exposes secrets via a "secret_ref" URL whose last segment is the
    # secret UUID; orca's create message includes the full ref. List by name.
    res = live_invoke("secret", "list", "-f", "value", "-c", "Name", "-c", "Secret href")
    assert res.exit_code == 0
    assert name in res.output

    # Find the secret ref so we can clean up by ID.
    line = next((line for line in res.output.splitlines() if name in line), "")
    secret_ref = line.split()[-1]
    cleanup(lambda: live_invoke("secret", "delete", secret_ref, "--yes"))
