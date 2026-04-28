"""Live e2e: Cinder block-storage."""

from __future__ import annotations

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


def test_volume_create_show_delete(live_invoke, cleanup, live_name):
    name = live_name("vol")

    res = live_invoke("volume", "create", "--name", name, "--size", "1")
    assert res.exit_code == 0, res.output
    vol_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("volume", "delete", vol_id, "--yes"))

    res = live_invoke("volume", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert vol_id in res.output

    res = live_invoke("volume", "show", vol_id, "-f", "value", "-c", "name")
    assert res.exit_code == 0
    assert name in res.output
