"""Tests for ``orca server create`` boot-mode selection (ephemeral vs BFV)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

IMG_ID = "55556666-7777-8888-9999-000011112222"
FLAVOR_WITH_DISK = "flav-disk-20"
FLAVOR_DISKLESS = "flav-disk-0"


def _mock_create_with_flavors(mock_client, flavors):
    """Wire a mock_client that answers GET /flavors/<id> and POST /servers."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    state = {"posted": {}}

    def _get(url, **kwargs):
        for fid, body in flavors.items():
            if url.endswith(f"/flavors/{fid}"):
                return {"flavor": {"id": fid, **body}}
        return {}

    def _post(url, **kwargs):
        state["posted"]["url"] = url
        state["posted"]["body"] = kwargs.get("json", {}).get("server", {})
        return {"server": {"id": "new-srv", "adminPass": "s3cr3t"}}

    mock_client.get = _get
    mock_client.post = _post
    return state


# ── auto-detection ──────────────────────────────────────────────────────────

class TestAutoDetect:

    def test_flavor_with_disk_defaults_to_boot_from_image(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_WITH_DISK: {"disk": 20}},
        )

        result = invoke(["server", "create",
                         "--name", "vm1",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert body["imageRef"] == IMG_ID
        assert "block_device_mapping_v2" not in body
        assert "from image" in result.output.lower()

    def test_diskless_flavor_falls_back_to_bfv(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_DISKLESS: {"disk": 0}},
        )

        result = invoke(["server", "create",
                         "--name", "vm2",
                         "--flavor", FLAVOR_DISKLESS,
                         "--image", IMG_ID,
                         "--disk-size", "30"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        bdm = body["block_device_mapping_v2"][0]
        assert bdm["destination_type"] == "volume"
        assert bdm["volume_size"] == 30
        assert "imageRef" not in body


# ── explicit flags ──────────────────────────────────────────────────────────

class TestExplicitFlags:

    def test_boot_from_volume_overrides_disk_flavor(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_WITH_DISK: {"disk": 20}},
        )

        result = invoke(["server", "create",
                         "--name", "vm3",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID,
                         "--boot-from-volume",
                         "--disk-size", "40"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert "block_device_mapping_v2" in body
        assert body["block_device_mapping_v2"][0]["volume_size"] == 40
        assert "imageRef" not in body

    def test_boot_from_image_on_flavor_with_disk(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_WITH_DISK: {"disk": 20}},
        )

        result = invoke(["server", "create",
                         "--name", "vm4",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID,
                         "--boot-from-image"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert body["imageRef"] == IMG_ID
        assert "block_device_mapping_v2" not in body

    def test_boot_from_image_on_diskless_flavor_errors(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_DISKLESS: {"disk": 0}},
        )

        result = invoke(["server", "create",
                         "--name", "vm5",
                         "--flavor", FLAVOR_DISKLESS,
                         "--image", IMG_ID,
                         "--boot-from-image"])

        assert result.exit_code != 0
        assert "disk=0" in result.output
        # The POST must not fire once we refuse the request.
        assert "body" not in state["posted"]

    def test_mutual_exclusion(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(
            mock_client, {FLAVOR_WITH_DISK: {"disk": 20}},
        )

        result = invoke(["server", "create",
                         "--name", "vm6",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID,
                         "--boot-from-image",
                         "--boot-from-volume"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
        assert "body" not in state["posted"]


# ── fallback when flavor lookup fails ───────────────────────────────────────

class TestFlavorLookupFailure:

    def test_unreachable_flavor_respects_boot_from_image_flag(
        self, invoke, config_dir, mock_client, sample_profile, monkeypatch,
    ):
        """When GET /flavors/<id> errors, the explicit --boot-from-image is honored."""
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(mock_client, {})

        def _get_fails(url, **kwargs):
            raise RuntimeError("neutron down")
        mock_client.get = _get_fails

        result = invoke(["server", "create",
                         "--name", "vm7",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID,
                         "--boot-from-image"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert body.get("imageRef") == IMG_ID
        assert "block_device_mapping_v2" not in body

    def test_unreachable_flavor_defaults_to_bfv_when_unspecified(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        """Without an explicit flag, an unknown flavor is safest as BFV."""
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_create_with_flavors(mock_client, {})

        def _get_fails(url, **kwargs):
            raise RuntimeError("boom")
        mock_client.get = _get_fails

        result = invoke(["server", "create",
                         "--name", "vm8",
                         "--flavor", FLAVOR_WITH_DISK,
                         "--image", IMG_ID])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert "block_device_mapping_v2" in body
