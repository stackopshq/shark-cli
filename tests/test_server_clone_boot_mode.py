"""Tests for ``orca server clone`` boot-mode selection (ephemeral vs BFV)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

SRC_ID = "11112222-3333-4444-5555-666677778888"
IMG_ID = "55556666-7777-8888-9999-000011112222"
NET_ID = "44445555-6666-7777-8888-999900001111"
VOL_ID = "22223333-4444-5555-6666-777788889999"
FLAVOR_WITH_DISK = "flav-disk-20"
FLAVOR_DISKLESS = "flav-disk-0"


def _mock_clone_environment(mock_client, flavor_id, flavor_disk):
    """Wire a mock_client that serves the GETs needed by `server clone`."""
    mock_client.compute_url = "https://nova.example.com/v2.1"
    mock_client.volume_url = "https://cinder.example.com/v3"
    state = {"posted": {}}

    def _get(url, **kwargs):
        if url.endswith(f"/flavors/{flavor_id}"):
            return {"flavor": {"id": flavor_id, "disk": flavor_disk}}
        if f"servers/{SRC_ID}/os-volume_attachments" in url:
            return {"volumeAttachments": [
                {"id": "att-1", "volumeId": VOL_ID, "device": "/dev/vda"},
            ]}
        if f"servers/{SRC_ID}/os-interface" in url:
            return {"interfaceAttachments": [
                {"net_id": NET_ID, "port_id": "p", "fixed_ips": []},
            ]}
        if f"servers/{SRC_ID}" in url:
            return {"server": {
                "id": SRC_ID, "name": "source",
                "flavor": {"id": flavor_id},
                "image": {"id": IMG_ID},
                "security_groups": [{"name": "default"}],
                "key_name": "k",
                "addresses": {},
            }}
        if f"volumes/{VOL_ID}" in url:
            return {"volume": {
                "size": 20,
                "volume_image_metadata": {"image_id": IMG_ID},
            }}
        return {}

    def _post(url, **kwargs):
        state["posted"]["url"] = url
        state["posted"]["body"] = kwargs.get("json", {}).get("server", {})
        return {"server": {"id": "clone-1"}}

    mock_client.get = _get
    mock_client.post = _post
    return state


class TestCloneAutoDetect:

    def test_flavor_with_disk_defaults_to_boot_from_image(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_clone_environment(mock_client, FLAVOR_WITH_DISK, 20)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst"])

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
        state = _mock_clone_environment(mock_client, FLAVOR_DISKLESS, 0)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert "block_device_mapping_v2" in body
        assert "imageRef" not in body


class TestCloneExplicitFlags:

    def test_boot_from_volume_override(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_clone_environment(mock_client, FLAVOR_WITH_DISK, 20)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst",
                         "--boot-from-volume", "--disk-size", "50"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert "block_device_mapping_v2" in body
        assert body["block_device_mapping_v2"][0]["volume_size"] == 50
        assert "imageRef" not in body

    def test_boot_from_image_override(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_clone_environment(mock_client, FLAVOR_WITH_DISK, 20)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst",
                         "--boot-from-image"])

        assert result.exit_code == 0, result.output
        body = state["posted"]["body"]
        assert body["imageRef"] == IMG_ID
        assert "block_device_mapping_v2" not in body

    def test_boot_from_image_on_diskless_errors(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_clone_environment(mock_client, FLAVOR_DISKLESS, 0)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst",
                         "--boot-from-image"])

        assert result.exit_code != 0
        assert "disk=0" in result.output
        assert "body" not in state["posted"]

    def test_mutual_exclusion(
        self, invoke, config_dir, mock_client, sample_profile,
    ):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _mock_clone_environment(mock_client, FLAVOR_WITH_DISK, 20)

        result = invoke(["server", "clone", SRC_ID, "--name", "dst",
                         "--boot-from-image", "--boot-from-volume"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
        assert "body" not in state["posted"]
