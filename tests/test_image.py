"""Tests for ``orca image`` commands."""

from __future__ import annotations

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
