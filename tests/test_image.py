"""Tests for ``orca image`` commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

IMG_ID = "11112222-3333-4444-5555-666677778888"
IMG_ID2 = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _image(img_id=IMG_ID, name="Ubuntu 22.04", status="active",
           size=2147483648, disk_format="qcow2", visibility="private",
           image_type=None, min_disk=20, min_ram=512):
    img = {
        "id": img_id,
        "name": name,
        "status": status,
        "size": size,
        "disk_format": disk_format,
        "container_format": "bare",
        "visibility": visibility,
        "min_disk": min_disk,
        "min_ram": min_ram,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-02T00:00:00Z",
    }
    if image_type:
        img["image_type"] = image_type
    return img


def _server(srv_id="srv-1", name="web-1", image_id=IMG_ID):
    return {
        "id": srv_id,
        "name": name,
        "image": {"id": image_id},
    }


def _setup_mock(mock_client, images=None, image_detail=None, servers=None):
    images = images if images is not None else []
    servers = servers if servers is not None else []
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.image_url = "https://glance.example.com"

    posted = {}
    patched = {}
    deleted = []
    put_urls = []

    def _get(url, **kwargs):
        if "/v2/images/" in url and "/file" not in url and "/tags/" not in url and "/actions/" not in url:
            return image_detail or (_image() if images else {})
        if "/v2/images" in url:
            return {"images": images}
        if "servers/detail" in url:
            return {"servers": servers}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        return {"id": "new-img-id", "name": body.get("name", ""), "status": "queued"}

    def _patch(url, **kwargs):
        patched["url"] = url
        patched["content"] = kwargs.get("content", b"")
        return {"id": IMG_ID, "name": "updated", "status": "active"}

    def _put(url, **kwargs):
        put_urls.append(url)

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.patch = _patch
    mock_client.put = _put
    mock_client.put_stream = lambda url, **kw: put_urls.append(url)
    mock_client.delete = _delete

    return {"posted": posted, "patched": patched, "deleted": deleted, "put_urls": put_urls}


# ══════════════════════════════════════════════════════════════════════════
#  image list
# ══════════════════════════════════════════════════════════════════════════


class TestImageList:

    def test_list_images(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, images=[
            _image(name="Ubuntu 22.04"),
            _image(img_id=IMG_ID2, name="Debian 12"),
        ])

        result = invoke(["image", "list"])
        assert result.exit_code == 0
        assert "Ubun" in result.output
        assert "Debi" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, images=[])

        result = invoke(["image", "list"])
        assert result.exit_code == 0
        assert "No images found" in result.output

    def test_list_sorted_by_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, images=[
            _image(name="Zulu"),
            _image(img_id=IMG_ID2, name="Alpha"),
        ])

        result = invoke(["image", "list"])
        alpha_pos = result.output.index("Alpha")
        zulu_pos = result.output.index("Zulu")
        assert alpha_pos < zulu_pos

    def test_list_shows_size_in_mb(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, images=[_image(size=104857600)])  # 100 MB

        result = invoke(["image", "list"])
        assert "100" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  image show
# ══════════════════════════════════════════════════════════════════════════


class TestImageShow:

    def test_show_image(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, image_detail=_image())

        result = invoke(["image", "show", IMG_ID])
        assert result.exit_code == 0
        assert "active" in result.output

    def test_show_displays_size_in_mb(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, image_detail=_image(size=1073741824))  # 1 GB = 1024 MB

        result = invoke(["image", "show", IMG_ID])
        assert "1024 MB" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  image create
# ══════════════════════════════════════════════════════════════════════════


class TestImageCreate:

    def test_create_image(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["image", "create", "my-image"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["name"] == "my-image"
        assert state["posted"]["disk_format"] == "qcow2"

    def test_create_with_options(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["image", "create", "raw-img",
                         "--disk-format", "raw", "--min-disk", "10",
                         "--min-ram", "512", "--visibility", "shared"])
        assert result.exit_code == 0
        assert state["posted"]["disk_format"] == "raw"
        assert state["posted"]["min_disk"] == 10
        assert state["posted"]["min_ram"] == 512
        assert state["posted"]["visibility"] == "shared"


# ══════════════════════════════════════════════════════════════════════════
#  image update
# ══════════════════════════════════════════════════════════════════════════


class TestImageUpdate:

    def test_update_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["image", "update", IMG_ID, "--name", "new-name"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["image", "update", IMG_ID])
        assert result.exit_code == 0
        assert "No properties" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  image deactivate / reactivate
# ══════════════════════════════════════════════════════════════════════════


class TestImageActivation:

    def test_deactivate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["image", "deactivate", IMG_ID])
        assert result.exit_code == 0
        assert "deactivated" in result.output.lower()

    def test_reactivate(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["image", "reactivate", IMG_ID])
        assert result.exit_code == 0
        assert "reactivated" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  image tag-add / tag-delete
# ══════════════════════════════════════════════════════════════════════════


class TestImageTags:

    def test_tag_add(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["image", "tag-add", IMG_ID, "prod"])
        assert result.exit_code == 0
        assert "prod" in result.output
        assert any("tags/prod" in u for u in state["put_urls"])

    def test_tag_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["image", "tag-delete", IMG_ID, "old-tag"])
        assert result.exit_code == 0
        assert "old-tag" in result.output
        assert any("tags/old-tag" in u for u in state["deleted"])


# ══════════════════════════════════════════════════════════════════════════
#  image delete
# ══════════════════════════════════════════════════════════════════════════


class TestImageDelete:

    def test_delete_image(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["image", "delete", IMG_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert any(IMG_ID in u for u in state["deleted"])

    def test_delete_aborts_without_confirm(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        _ = invoke(["image", "delete", IMG_ID], input="n\n")
        assert len(state["deleted"]) == 0


# ══════════════════════════════════════════════════════════════════════════
#  image unused
# ══════════════════════════════════════════════════════════════════════════


class TestImageUnused:

    def test_unused_finds_images(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    images=[
                        _image(img_id=IMG_ID, name="used-img"),
                        _image(img_id=IMG_ID2, name="unused-img"),
                    ],
                    servers=[_server(image_id=IMG_ID)])

        result = invoke(["image", "unused"])
        assert result.exit_code == 0
        assert "unus" in result.output
        assert "1 unused" in result.output

    def test_unused_all_in_use(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    images=[_image(img_id=IMG_ID)],
                    servers=[_server(image_id=IMG_ID)])

        result = invoke(["image", "unused"])
        assert result.exit_code == 0
        assert "All active images are in use" in result.output

    def test_unused_skips_snapshots(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    images=[_image(img_id=IMG_ID2, name="snap", image_type="snapshot")],
                    servers=[])

        result = invoke(["image", "unused"])
        assert result.exit_code == 0
        assert "All active images are in use" in result.output

    def test_unused_include_snapshots(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    images=[_image(img_id=IMG_ID2, name="snap", image_type="snapshot")],
                    servers=[])

        result = invoke(["image", "unused", "--include-snapshots"])
        assert result.exit_code == 0
        assert "snap" in result.output

    def test_unused_skips_non_active(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client,
                    images=[_image(img_id=IMG_ID2, status="deactivated")],
                    servers=[])

        result = invoke(["image", "unused"])
        assert "All active images are in use" in result.output

    def test_unused_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client,
                            images=[_image(img_id=IMG_ID2, name="orphan")],
                            servers=[])

        result = invoke(["image", "unused", "--delete", "-y"])
        assert result.exit_code == 0
        assert "1 deleted" in result.output
        assert len(state["deleted"]) == 1

    def test_unused_delete_aborts(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client,
                            images=[_image(img_id=IMG_ID2, name="orphan")],
                            servers=[])

        _ = invoke(["image", "unused", "--delete"], input="n\n")
        assert len(state["deleted"]) == 0


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestImageHelp:

    def test_image_help(self, invoke):
        result = invoke(["image", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "update", "upload", "download",
                    "delete", "deactivate", "reactivate", "tag-add", "tag-delete",
                    "shrink", "unused"):
            assert cmd in result.output

    def test_image_list_help(self, invoke):
        result = invoke(["image", "list", "--help"])
        assert result.exit_code == 0

    def test_image_unused_help(self, invoke):
        result = invoke(["image", "unused", "--help"])
        assert result.exit_code == 0
        assert "--delete" in result.output
        assert "--include-snapshots" in result.output

    def test_image_shrink_help(self, invoke):
        result = invoke(["image", "shrink", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════
#  image upload — streaming chunked PUT to /v2/images/{id}/file
# ══════════════════════════════════════════════════════════════════════════

GL = "https://glance.example.com"


class TestImageUpload:
    """`orca image upload` streams the file in 256 KB chunks via PUT."""

    def _mock_put(self, mock_client, status_code=204, body=b""):
        """Patch _http.put to record the call and consume the streamed body."""
        captured: dict = {}

        def _put(url, headers=None, content=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers or {}
            captured["chunks"] = list(content) if content is not None else []
            resp = MagicMock()
            resp.status_code = status_code
            resp.is_success = 200 <= status_code < 300
            resp.text = body.decode() if isinstance(body, bytes) else str(body)
            return resp

        mock_client.image_url = GL
        mock_client._http.put = _put
        mock_client._headers = lambda: {"X-Auth-Token": "tok"}
        return captured

    def test_upload_posts_to_file_endpoint(self, invoke, mock_client, tmp_path):
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"x" * 1024)
        captured = self._mock_put(mock_client)

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code == 0, result.output
        assert captured["url"] == f"{GL}/v2/images/{IMG_ID}/file"

    def test_upload_sets_content_type_and_length(self, invoke, mock_client, tmp_path):
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"abcd" * 256)  # 1024 bytes
        captured = self._mock_put(mock_client)

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code == 0
        assert captured["headers"]["Content-Type"] == "application/octet-stream"
        assert captured["headers"]["Content-Length"] == "1024"

    def test_upload_streams_in_256kb_chunks(self, invoke, mock_client, tmp_path):
        """700 KB file → 3 chunks of 256/256/188 KB (no whole-file read)."""
        size = 256 * 1024 * 2 + 188 * 1024  # 700 KB
        img_file = tmp_path / "big.img"
        img_file.write_bytes(b"z" * size)
        captured = self._mock_put(mock_client)

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code == 0
        chunks = captured["chunks"]
        assert len(chunks) == 3
        assert len(chunks[0]) == 256 * 1024
        assert len(chunks[1]) == 256 * 1024
        assert len(chunks[2]) == 188 * 1024
        assert sum(len(c) for c in chunks) == size

    def test_upload_small_file_single_chunk(self, invoke, mock_client, tmp_path):
        """File smaller than chunk size → one chunk."""
        img_file = tmp_path / "small.img"
        img_file.write_bytes(b"tiny")
        captured = self._mock_put(mock_client)

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code == 0
        assert captured["chunks"] == [b"tiny"]

    def test_upload_server_error_raises_apierror(self, invoke, mock_client, tmp_path):
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"data")
        self._mock_put(mock_client, status_code=500, body=b"boom")

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code != 0
        assert "500" in result.output or "boom" in result.output.lower()

    def test_upload_auth_error_raises(self, invoke, mock_client, tmp_path):
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"data")
        self._mock_put(mock_client, status_code=401)

        result = invoke(["image", "upload", IMG_ID, str(img_file)])

        assert result.exit_code != 0
        assert "auth" in result.output.lower() or "authentic" in result.output.lower() \
            or "expired" in result.output.lower()
