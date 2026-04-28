"""Live e2e: comprehensive Swift object-store coverage.

Covers ``container`` (8) + ``object`` (17 — incl. account-set/unset,
container CRUD aliases, object up/down/delete/save, stats, tree).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_container_top_level_full(live_invoke, cleanup, live_name):
    name = live_name("cont")
    res = live_invoke("container", "create", name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("container", "delete", name, "--yes"))

    res = live_invoke("container", "set", name,
                      "--property", "X-Live-Test=true")
    assert res.exit_code == 0, res.output

    res = live_invoke("container", "list", "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert name in res.output

    res = live_invoke("container", "show", name)
    assert res.exit_code == 0, res.output

    res = live_invoke("container", "stats")
    assert res.exit_code == 0, res.output

    res = live_invoke("container", "unset", name, "--property", "X-Live-Test")
    assert res.exit_code == 0, res.output


def test_object_upload_download_lifecycle(live_invoke, cleanup, live_name, tmp_path):
    name = live_name("cont")
    res = live_invoke("container", "create", name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("container", "delete", name, "--yes", "--recursive"))

    # Upload an object
    src = tmp_path / "hello.txt"
    src.write_text("hello, live-test\n")
    obj_name = "greeting.txt"
    res = live_invoke("object", "upload", name, str(src),
                      "--name", obj_name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("object", "delete", name, obj_name, "--yes"))

    # List
    res = live_invoke("object", "list", name, "-f", "value", "-c", "Name")
    assert res.exit_code == 0
    assert obj_name in res.output

    # Show metadata
    res = live_invoke("object", "show", name, obj_name)
    assert res.exit_code == 0, res.output

    # Download to a different file, verify content
    dest = tmp_path / "downloaded.txt"
    res = live_invoke("object", "download", name, obj_name,
                      "--file", str(dest))
    assert res.exit_code == 0, res.output
    assert dest.read_text() == "hello, live-test\n"

    # Set metadata
    res = live_invoke("object", "set", name, obj_name,
                      "--property", "X-Live=yes")
    assert res.exit_code == 0, res.output

    # Unset metadata
    res = live_invoke("object", "unset", name, obj_name, "--property", "X-Live")
    assert res.exit_code == 0, res.output

    # Stats (account-level)
    res = live_invoke("object", "stats")
    assert res.exit_code == 0, res.output

    # Tree (account view)
    res = live_invoke("object", "tree")
    assert res.exit_code == 0, res.output


def test_object_account_metadata(live_invoke):
    res = live_invoke("object", "account", "set",
                      "--property", "X-Live-Account=yes")
    assert res.exit_code == 0, res.output

    res = live_invoke("object", "account", "unset",
                      "--property", "X-Live-Account")
    assert res.exit_code == 0, res.output


def test_container_save(live_invoke, cleanup, live_name, tmp_path):
    name = live_name("cont")
    res = live_invoke("container", "create", name)
    assert res.exit_code == 0, res.output
    cleanup(lambda: live_invoke("container", "delete", name, "--yes", "--recursive"))

    # Drop a small object
    src = tmp_path / "f.txt"
    src.write_text("backup data")
    res = live_invoke("object", "upload", name, str(src), "--name", "f.txt")
    assert res.exit_code == 0, res.output

    out_dir = tmp_path / "saved"
    res = live_invoke("container", "save", name, "--output-dir", str(out_dir))
    assert res.exit_code == 0, res.output
    assert (out_dir / "f.txt").exists()
