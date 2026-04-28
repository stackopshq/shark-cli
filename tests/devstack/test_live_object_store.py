"""Live e2e: Swift object-store containers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_container_create_list_delete(live_invoke, cleanup, live_name):
    name = live_name("cont")

    res = live_invoke("container", "create", name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("container", "delete", name, "--yes"))

    res = live_invoke("container", "list", "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output
