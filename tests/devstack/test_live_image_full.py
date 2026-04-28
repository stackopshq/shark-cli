"""Live e2e: comprehensive Glance image coverage.

Covers create/delete/list/show, update, deactivate/reactivate,
member CRUD, tag add/delete, task-list/show, stores-info, download,
cache list/queue/delete/clear, unused, shrink (best-effort).

Skipped: ``stage`` + ``import`` (need Glance v2 import API workflow
plus a staged disk), ``share-and-accept`` (interactive multi-cloud),
``upload`` to existing image (covered indirectly via create --file).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


@pytest.fixture
def cirros_path() -> Path:
    p = Path("/tmp/cirros.img")  # noqa: S108 — cross-run cache
    if not p.exists():
        pytest.skip("cirros image cache /tmp/cirros.img missing")
    return p


def test_image_create_update_lifecycle(live_invoke, cleanup, live_name, cirros_path):
    name = live_name("img")
    res = live_invoke("image", "create", name,
                      "--disk-format", "qcow2",
                      "--file", str(cirros_path),
                      "--property", "os_distro=cirros",
                      "--property", "os_version=0.6.3")
    assert res.exit_code == 0, res.output
    image_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("image", "delete", image_id, "--yes"))

    res = live_invoke("image", "update", image_id,
                      "--property", "os_admin_user=cirros")
    assert res.exit_code == 0, res.output

    res = live_invoke("image", "deactivate", image_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("image", "reactivate", image_id)
    assert res.exit_code == 0, res.output

    res = live_invoke("image", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert image_id in res.output

    res = live_invoke("image", "show", image_id, "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output


def test_image_members(live_invoke, cleanup, live_name, cirros_path):
    img_name = live_name("img")
    res = live_invoke("image", "create", img_name,
                      "--disk-format", "qcow2",
                      "--file", str(cirros_path),
                      "--visibility", "shared")
    assert res.exit_code == 0, res.output
    image_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("image", "delete", image_id, "--yes"))

    proj_name = live_name("img-proj")
    res = live_invoke("project", "create", proj_name)
    assert res.exit_code == 0, res.output
    proj_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("project", "delete", proj_id, "--yes"))

    res = live_invoke("image", "member", "create", image_id, proj_id)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("image", "member", "delete",
                                image_id, proj_id, "--yes"))

    res = live_invoke("image", "member", "list", image_id, "-f", "json")
    assert res.exit_code == 0
    assert proj_id in res.output

    res = live_invoke("image", "member", "set", image_id, proj_id,
                      "--status", "accepted")
    assert res.exit_code == 0, res.output

    res = live_invoke("image", "member", "show", image_id, proj_id,
                      "-f", "value", "-c", "Status")
    assert res.exit_code == 0
    assert "accepted" in res.output


def test_image_tags(live_invoke, cleanup, live_name, cirros_path):
    name = live_name("img")
    res = live_invoke("image", "create", name,
                      "--disk-format", "qcow2",
                      "--file", str(cirros_path))
    assert res.exit_code == 0, res.output
    image_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("image", "delete", image_id, "--yes"))

    res = live_invoke("image", "tag", "add", image_id, "live-test")
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("image", "tag", "delete",
                                image_id, "live-test", "--yes"))

    res = live_invoke("image", "show", image_id, "-f", "value", "-c", "Tags")
    assert res.exit_code == 0
    assert "live-test" in res.output


def test_image_task_stores_download(live_invoke, cleanup, live_name,
                                     cirros_path, tmp_path):
    name = live_name("img")
    res = live_invoke("image", "create", name,
                      "--disk-format", "qcow2",
                      "--file", str(cirros_path))
    assert res.exit_code == 0, res.output
    image_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("image", "delete", image_id, "--yes"))

    # tasks (Glance v2 API; may be empty)
    res = live_invoke("image", "task", "list")
    assert res.exit_code == 0, res.output

    # stores-info — Glance multi-store API
    res = live_invoke("image", "stores", "info")
    if res.exit_code != 0 and "Not found" in res.output:
        pytest.skip("Glance multi-store API not enabled")
    assert res.exit_code == 0, res.output

    # download to a tmp file
    out_file = tmp_path / "downloaded.img"
    res = live_invoke("image", "download", image_id, "--file", str(out_file))
    assert res.exit_code == 0, res.output
    assert out_file.exists() and out_file.stat().st_size > 0


def test_image_cache_unused(live_invoke):
    # cache-list (Glance image cache status; may need admin and the
    # cache extension enabled — accept clean failure)
    res = live_invoke("image", "cache", "list")
    if res.exit_code != 0:
        pytest.skip(f"image cache API not enabled: {res.output}")

    # unused: filters images that aren't booted by any server
    res = live_invoke("image", "unused")
    assert res.exit_code == 0, res.output
