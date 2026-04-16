"""Tests for ``orca image import`` and ``orca image cache-*``."""

from __future__ import annotations

IMG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
GL  = "https://glance.example.com"


def _setup(mock_client):
    mock_client.image_url = GL


# ══════════════════════════════════════════════════════════════════════════
#  image import
# ══════════════════════════════════════════════════════════════════════════

class TestImageImport:

    def test_web_download(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG,
                         "--method", "web-download",
                         "--uri", "https://example.com/image.img"])
        assert result.exit_code == 0
        assert mock_client.post.called
        body = mock_client.post.call_args[1]["json"]
        assert body["method"]["name"] == "web-download"
        assert body["method"]["uri"] == "https://example.com/image.img"

    def test_web_download_calls_correct_url(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["image", "import", IMG, "--uri", "https://example.com/image.img"])
        url = mock_client.post.call_args[0][0]
        assert f"/v2/images/{IMG}/import" in url

    def test_web_download_requires_uri(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG, "--method", "web-download"])
        assert result.exit_code != 0
        assert "uri" in result.output.lower()

    def test_glance_direct(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG, "--method", "glance-direct"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["method"]["name"] == "glance-direct"

    def test_copy_image(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG,
                         "--method", "copy-image",
                         "--store", "ceph1", "--store", "ceph2"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["method"]["name"] == "copy-image"
        assert "ceph1" in body["stores"]
        assert "ceph2" in body["stores"]

    def test_default_method_is_web_download(self, invoke, mock_client):
        _setup(mock_client)
        invoke(["image", "import", IMG, "--uri", "https://example.com/img"])
        body = mock_client.post.call_args[1]["json"]
        assert body["method"]["name"] == "web-download"

    def test_shows_image_id_in_output(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG, "--method", "glance-direct"])
        assert IMG[:8] in result.output

    def test_invalid_method_rejected(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "import", IMG, "--method", "unknown"])
        assert result.exit_code != 0

    def test_help(self, invoke):
        result = invoke(["image", "import", "--help"])
        assert result.exit_code == 0
        assert "web-download" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  image cache-list
# ══════════════════════════════════════════════════════════════════════════

class TestImageCacheList:

    def test_list_cached_and_queued(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {
            "cached_images": [IMG],
            "queued_images": ["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"],
        }
        result = invoke(["image", "cache-list"])
        assert result.exit_code == 0
        assert "cached" in result.output
        assert "queued" in result.output

    def test_list_calls_correct_url(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"cached_images": [], "queued_images": []}
        invoke(["image", "cache-list"])
        url = mock_client.get.call_args[0][0]
        assert "/v2/cache" in url

    def test_list_empty(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"cached_images": [], "queued_images": []}
        result = invoke(["image", "cache-list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "Cache" in result.output

    def test_help(self, invoke):
        assert invoke(["image", "cache-list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  image cache-queue
# ══════════════════════════════════════════════════════════════════════════

class TestImageCacheQueue:

    def test_queue(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-queue", IMG])
        assert result.exit_code == 0
        assert mock_client.put.called
        url = mock_client.put.call_args[0][0]
        assert f"/v2/cache/{IMG}" in url

    def test_shows_confirmation(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-queue", IMG])
        assert "queue" in result.output.lower() or IMG[:8] in result.output

    def test_help(self, invoke):
        assert invoke(["image", "cache-queue", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  image cache-delete
# ══════════════════════════════════════════════════════════════════════════

class TestImageCacheDelete:

    def test_delete_yes(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-delete", IMG, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        url = mock_client.delete.call_args[0][0]
        assert f"/v2/cache/{IMG}" in url

    def test_delete_requires_confirm(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-delete", IMG], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["image", "cache-delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  image cache-clear
# ══════════════════════════════════════════════════════════════════════════

class TestImageCacheClear:

    def test_clear_yes(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-clear", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        url = mock_client.delete.call_args[0][0]
        assert url.endswith("/v2/cache")

    def test_clear_requires_confirm(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-clear"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_clear_confirm_yes(self, invoke, mock_client):
        _setup(mock_client)
        result = invoke(["image", "cache-clear"], input="y\n")
        assert result.exit_code == 0
        assert mock_client.delete.called

    def test_help(self, invoke):
        assert invoke(["image", "cache-clear", "--help"]).exit_code == 0
