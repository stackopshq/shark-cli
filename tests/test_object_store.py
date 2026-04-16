"""Tests for ``orca object`` commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────


def _fake_response(status_code=200, content=b"data", headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.content = content
    resp.text = content.decode() if isinstance(content, bytes) else str(content)
    resp.headers = headers or {}
    return resp


def _setup_mock(mock_client):
    mock_client.object_store_url = "https://swift.example.com/v1/AUTH_proj"
    mock_client._headers = lambda: {"X-Auth-Token": "fake-token"}

    http = MagicMock()
    mock_client._http = http

    deleted = []
    posted = {}

    def _get(url, **kwargs):
        # Container list (account level)
        if url.endswith("?format=json") and "/AUTH_proj?" in url:
            return [
                {"name": "docs", "count": 5, "bytes": 10240},
                {"name": "backups", "count": 2, "bytes": 2048},
            ]
        # Object list
        if "docs?" in url and "format=json" in url:
            return [
                {"name": "readme.txt", "bytes": 1024, "last_modified": "2025-01-01",
                 "content_type": "text/plain", "hash": "abc123"},
                {"name": "notes.md", "bytes": 512, "last_modified": "2025-01-02",
                 "content_type": "text/markdown", "hash": "def456"},
            ]
        return []

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.delete = _delete

    # HEAD responses
    def _head(url, **kwargs):
        if "AUTH_proj/" in url and url.count("/") == 6:
            # Object HEAD
            return _fake_response(headers={
                "content-type": "text/plain",
                "content-length": "1024",
                "etag": "abc123",
                "last-modified": "2025-01-01",
                "accept-ranges": "bytes",
            })
        if "AUTH_proj/" in url:
            # Container HEAD
            return _fake_response(headers={
                "x-container-object-count": "5",
                "x-container-bytes-used": "10240",
                "x-container-read": "",
                "x-container-write": "",
                "x-storage-policy": "default",
            })
        # Account HEAD
        return _fake_response(headers={
            "x-account-container-count": "3",
            "x-account-object-count": "42",
            "x-account-bytes-used": "1048576",
            "x-account-project-domain-id": "default",
        })

    http.head = _head

    def _put(url, **kwargs):
        return _fake_response(201)

    http.put = _put

    def _http_get(url, **kwargs):
        return _fake_response(200, content=b"file content here")

    http.get = _http_get

    def _post(url, **kwargs):
        return _fake_response(204)

    http.post = _post

    return {"deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  stats
# ══════════════════════════════════════════════════════════════════════════


class TestObjectStats:

    def test_stats(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "stats"])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "3" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container list
# ══════════════════════════════════════════════════════════════════════════


class TestContainerList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "list"])
        assert result.exit_code == 0
        assert "docs" in result.output
        assert "backups" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.object_store_url = "https://swift.example.com/v1/AUTH_proj"
        mock_client.get = lambda url, **kw: []

        result = invoke(["container", "list"])
        assert result.exit_code == 0
        assert "No containers found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container show
# ══════════════════════════════════════════════════════════════════════════


class TestContainerShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "show", "docs"])
        assert result.exit_code == 0
        assert "docs" in result.output
        assert "5" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  container create
# ══════════════════════════════════════════════════════════════════════════


class TestContainerCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "create", "new-bucket"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  container delete
# ══════════════════════════════════════════════════════════════════════════


class TestContainerDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["container", "delete", "old-bucket"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

    def test_delete_recursive(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        # Override get to return objects for the container
        orig_get = mock_client.get
        def _get(url, **kwargs):
            if "old-bucket?" in url:
                return [{"name": "file1.txt"}, {"name": "file2.txt"}]
            return orig_get(url, **kwargs)
        mock_client.get = _get

        result = invoke(["container", "delete", "old-bucket", "--recursive"])
        assert result.exit_code == 0
        assert len(state["deleted"]) == 3  # 2 objects + 1 container


# ══════════════════════════════════════════════════════════════════════════
#  list (objects)
# ══════════════════════════════════════════════════════════════════════════


class TestObjectList:

    def test_list_objects(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["object", "list", "docs"])
        assert result.exit_code == 0
        assert "readme" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.object_store_url = "https://swift.example.com/v1/AUTH_proj"
        mock_client.get = lambda url, **kw: []

        result = invoke(["object", "list", "empty-bucket"])
        assert result.exit_code == 0
        assert "No objects found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  show (object)
# ══════════════════════════════════════════════════════════════════════════


class TestObjectShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["object", "show", "docs", "readme.txt"])
        assert result.exit_code == 0
        assert "readme.txt" in result.output
        assert "1024" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  delete (objects)
# ══════════════════════════════════════════════════════════════════════════


class TestObjectDelete:

    def test_delete_objects(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["object", "delete", "docs", "file1.txt", "file2.txt"])
        assert result.exit_code == 0
        assert "2 object(s)" in result.output
        assert len(state["deleted"]) == 2


# ══════════════════════════════════════════════════════════════════════════
#  container-set
# ══════════════════════════════════════════════════════════════════════════


class TestContainerSet:

    def test_set_metadata(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "set", "docs", "--property", "env=prod"])
        assert result.exit_code == 0
        assert "Metadata set" in result.output

    def test_set_invalid_format(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["container", "set", "docs", "--property", "badformat"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  container unset
# ══════════════════════════════════════════════════════════════════════════


class TestContainerUnset:

    def test_unset_metadata(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["container", "unset", "docs", "--property", "env"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert any("X-Remove-Container-Meta-env" in k for k in posted_headers)

    def test_unset_multiple_keys(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["container", "unset", "docs", "--property", "env", "--property", "owner"])
        assert result.exit_code == 0
        assert any("X-Remove-Container-Meta-env" in k for k in posted_headers)
        assert any("X-Remove-Container-Meta-owner" in k for k in posted_headers)


# ══════════════════════════════════════════════════════════════════════════
#  object unset
# ══════════════════════════════════════════════════════════════════════════


class TestObjectUnset:

    def test_unset_metadata(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["object", "unset", "docs", "readme.txt", "--property", "author"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert any("X-Remove-Object-Meta-author" in k for k in posted_headers)

    def test_unset_multiple_keys(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["object", "unset", "docs", "readme.txt",
                         "--property", "author", "--property", "version"])
        assert result.exit_code == 0
        assert any("X-Remove-Object-Meta-author" in k for k in posted_headers)
        assert any("X-Remove-Object-Meta-version" in k for k in posted_headers)


# ══════════════════════════════════════════════════════════════════════════
#  account-set / account-unset
# ══════════════════════════════════════════════════════════════════════════


class TestAccountSet:

    def test_account_set(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["object", "account-set", "--property", "quota=100GB"])
        assert result.exit_code == 0
        assert "set" in result.output.lower()
        assert any("X-Account-Meta-quota" in k for k in posted_headers)

    def test_account_set_invalid_format(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["object", "account-set", "--property", "badformat"])
        assert result.exit_code != 0

    def test_account_unset(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["object", "account-unset", "--property", "quota"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert any("X-Remove-Account-Meta-quota" in k for k in posted_headers)

    def test_account_unset_multiple(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        posted_headers = {}

        def _post(url, **kwargs):
            posted_headers.update(kwargs.get("headers", {}))
            return _fake_response(204)

        mock_client._http.post = _post

        result = invoke(["object", "account-unset", "--property", "quota", "--property", "tier"])
        assert result.exit_code == 0
        assert any("X-Remove-Account-Meta-quota" in k for k in posted_headers)
        assert any("X-Remove-Account-Meta-tier" in k for k in posted_headers)


# ══════════════════════════════════════════════════════════════════════════
#  tree
# ══════════════════════════════════════════════════════════════════════════


class TestObjectTree:

    def test_tree_account(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["object", "tree"])
        assert result.exit_code == 0
        assert "docs" in result.output
        assert "backups" in result.output

    def test_tree_container(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["object", "tree", "docs"])
        assert result.exit_code == 0
        assert "readme" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  _human_size
# ══════════════════════════════════════════════════════════════════════════


class TestHumanSize:

    def test_bytes(self):
        from orca_cli.commands.object_store import _human_size
        assert _human_size(500) == "500 B"

    def test_kb(self):
        from orca_cli.commands.object_store import _human_size
        assert "KB" in _human_size(2048)

    def test_mb(self):
        from orca_cli.commands.object_store import _human_size
        assert "MB" in _human_size(5 * 1024 * 1024)

    def test_none(self):
        from orca_cli.commands.object_store import _human_size
        assert _human_size(None) == "—"

    def test_empty(self):
        from orca_cli.commands.object_store import _human_size
        assert _human_size("") == "—"


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestObjectHelp:

    def test_object_help(self, invoke):
        result = invoke(["object", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "upload", "download", "delete", "unset", "tree",
                    "account-set", "account-unset"):
            assert cmd in result.output

    def test_container_help(self, invoke):
        result = invoke(["container", "--help"])
        assert result.exit_code == 0
        for cmd in ("stats", "list", "show", "create", "delete", "set", "unset", "save"):
            assert cmd in result.output

    def test_upload_help(self, invoke):
        result = invoke(["object", "upload", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
