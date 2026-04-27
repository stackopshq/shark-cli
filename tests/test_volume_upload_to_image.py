"""Tests for ``orca volume upload-to-image``."""

from __future__ import annotations

import json as _json

import pytest

from orca_cli.core.config import save_profile, set_active_profile

VOL_ID = "11112222-3333-4444-5555-666677778888"
IMG_ID = "aaaa1111-bbbb-2222-cccc-333333333333"


def _vol(status="available", name="src-vol"):
    return {
        "id": VOL_ID, "name": name, "status": status, "size": 10,
        "bootable": "true", "attachments": [],
    }


def _img(status="queued", size=None, **extra):
    img = {"id": IMG_ID, "name": "my-image", "status": status,
           "disk_format": "qcow2", "container_format": "bare",
           "visibility": "private"}
    if size is not None:
        img["size"] = size
    img.update(extra)
    return img


class _Recorder:
    """Capture HTTP-shaped calls made through the mock OrcaClient."""

    def __init__(self):
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, bytes, str | None]] = []
        self.gets: list[tuple[str, dict | None]] = []

    def install(self, mock_client, *,
                vol_status: str = "available",
                image_states: list[dict] | None = None,
                upload_response_image_id: str | None = IMG_ID):
        """Wire the recorder onto a mock OrcaClient.

        ``image_states`` is an iterable of image dicts returned by
        successive GETs on /images/{id} — used to script the polling loop.
        """
        mock_client.volume_url = "https://cinder.example.com/v3"
        mock_client.image_url = "https://glance.example.com"

        states = list(image_states) if image_states else [_img(status="queued")]
        # Index iterator so repeated GETs walk through scripted states.
        state_iter = iter(states)
        last_state = {"img": next(state_iter, states[0])}

        def _get(url, **kwargs):
            self.gets.append((url, kwargs.get("params")))
            if f"/volumes/{VOL_ID}" in url and "/action" not in url:
                return {"volume": _vol(status=vol_status)}
            if "/volumes/detail" in url:
                params = kwargs.get("params") or {}
                # Name lookup: return one match for any "name" param.
                if params.get("name"):
                    return {"volumes": [_vol(name=params["name"])]}
                return {"volumes": []}
            if f"/images/{IMG_ID}" in url:
                # Advance to the next scripted state on each call, sticking
                # at the last one once exhausted.
                try:
                    last_state["img"] = next(state_iter)
                except StopIteration:
                    pass
                return last_state["img"]
            return {}

        def _post(url, **kwargs):
            body = kwargs.get("json", {})
            self.posts.append((url, body))
            if "/volumes/" in url and "/action" in url:
                if upload_response_image_id is None:
                    return {"os-volume_upload_image": {"status": "uploading"}}
                return {
                    "os-volume_upload_image": {
                        "id": VOL_ID,
                        "image_id": upload_response_image_id,
                        "status": "uploading",
                        "image_name": body.get("os-volume_upload_image", {}).get("image_name"),
                    },
                }
            return {}

        def _patch(url, content=None, content_type=None, **kwargs):
            self.patches.append((url, content, content_type))
            return _img(status="queued")

        mock_client.get = _get
        mock_client.post = _post
        mock_client.patch = _patch
        return self


@pytest.fixture
def setup(mock_client, sample_profile, config_dir):
    save_profile("p", sample_profile)
    set_active_profile("p")
    return mock_client


# ── happy path ────────────────────────────────────────────────────────────


def test_happy_path_with_property_and_wait(monkeypatch, invoke, setup):
    """Available volume → POST action, PATCH property, poll to active."""
    rec = _Recorder().install(
        setup,
        image_states=[
            _img(status="queued"),                     # initial PATCH read
            _img(status="saving", size=256_000_000),   # poll #1
            _img(status="saving", size=512_000_000),   # poll #2 (spinner update)
            _img(status="active", size=1_073_741_824,  # poll #3 (terminal)
                 checksum="abc123",
                 os_hash_algo="sha512", os_hash_value="deadbeef"),
        ],
    )
    # No real sleeping during the polling loop.
    monkeypatch.setattr("orca_cli.commands.volume.time.sleep", lambda *_: None)

    result = invoke([
        "volume", "upload-to-image", VOL_ID, "my-image",
        "--disk-format", "qcow2",
        "--property", "os_distro=ubuntu",
        "--wait",
    ])

    assert result.exit_code == 0, result.output
    # One POST to the upload action, body matches.
    action_posts = [(u, b) for u, b in rec.posts if "/action" in u]
    assert len(action_posts) == 1
    url, body = action_posts[0]
    assert url.endswith(f"/volumes/{VOL_ID}/action")
    payload = body["os-volume_upload_image"]
    assert payload["image_name"] == "my-image"
    assert payload["disk_format"] == "qcow2"
    assert payload["force"] is False
    # ``visibility`` and ``protected`` must NOT be present when the user
    # didn't pass the corresponding flags — older Cinder microversions
    # reject the action with HTTP 400 if those keys appear.
    assert "visibility" not in payload
    assert "protected" not in payload

    # One PATCH to the resulting image with the property added.
    assert len(rec.patches) == 1
    patch_url, content, content_type = rec.patches[0]
    assert patch_url.endswith(f"/v2/images/{IMG_ID}")
    assert content_type == "application/openstack-images-v2.1-json-patch"
    ops = _json.loads(content)
    assert ops == [{"op": "add", "path": "/os_distro", "value": "ubuntu"}]

    # Final output mentions the image UUID and active state.
    assert IMG_ID in result.output
    assert "active" in result.output.lower()


# ── in-use volume guards ──────────────────────────────────────────────────


def test_in_use_without_force_aborts_before_post(invoke, setup):
    rec = _Recorder().install(setup, vol_status="in-use")

    result = invoke(["volume", "upload-to-image", VOL_ID, "my-image"])

    assert result.exit_code != 0
    assert not [u for u, _ in rec.posts if "/action" in u], \
        "POST must NOT be issued when --force is missing"
    out = result.output + (result.stderr_bytes or b"").decode(errors="replace")
    assert "in-use" in out
    assert "--force" in out


def test_in_use_with_force_sends_force_true(invoke, setup):
    rec = _Recorder().install(setup, vol_status="in-use")

    result = invoke(["volume", "upload-to-image", VOL_ID, "img", "--force"])

    assert result.exit_code == 0, result.output
    action_posts = [(u, b) for u, b in rec.posts if "/action" in u]
    assert len(action_posts) == 1
    body = action_posts[0][1]
    assert body["os-volume_upload_image"]["force"] is True


# ── failure during --wait ────────────────────────────────────────────────


def test_killed_during_wait_exits_nonzero(monkeypatch, invoke, setup):
    rec = _Recorder().install(
        setup,
        image_states=[
            _img(status="saving"),
            _img(status="killed", message="qemu-img conversion failed"),
        ],
    )
    monkeypatch.setattr("orca_cli.commands.volume.time.sleep", lambda *_: None)

    result = invoke(["volume", "upload-to-image", VOL_ID, "img", "--wait"])

    assert result.exit_code != 0
    out = result.output + (result.stderr_bytes or b"").decode(errors="replace")
    assert "killed" in out.lower()
    assert "qemu-img conversion failed" in out
    # Action POST should still have been issued before the failed wait.
    assert len([u for u, _ in rec.posts if "/action" in u]) == 1
    # No PATCH because no --property.
    assert rec.patches == []


# ── property validation ──────────────────────────────────────────────────


def test_invalid_property_key_aborts_before_any_call(invoke, setup):
    rec = _Recorder().install(setup)

    result = invoke([
        "volume", "upload-to-image", VOL_ID, "img",
        "--property", "bad key=v",
    ])

    assert result.exit_code != 0
    assert rec.posts == []
    assert rec.patches == []


def test_property_value_with_special_chars_forwarded_intact(invoke, setup):
    rec = _Recorder().install(setup)
    url_value = "https://x?a=1&b=2"

    result = invoke([
        "volume", "upload-to-image", VOL_ID, "img",
        "--property", f"url={url_value}",
    ])

    assert result.exit_code == 0, result.output
    assert len(rec.patches) == 1
    ops = _json.loads(rec.patches[0][1])
    assert ops == [{"op": "add", "path": "/url", "value": url_value}]


# ── defensive: missing image_id in Cinder response ───────────────────────


def test_missing_image_id_in_response_aborts(invoke, setup):
    """If Cinder accepts the action but doesn't return an image_id, fail loudly."""
    rec = _Recorder().install(setup, upload_response_image_id=None)

    result = invoke(["volume", "upload-to-image", VOL_ID, "img"])

    assert result.exit_code != 0
    out = result.output + (result.stderr_bytes or b"").decode(errors="replace")
    assert "image_id" in out
    # No PATCH should be attempted without an image to target.
    assert rec.patches == []


# ── older-microversion compatibility ────────────────────────────────────


def test_default_omits_visibility_and_protected(invoke, setup):
    """Without explicit flags, the body must not carry visibility/protected.

    Mirrors a strict Cinder that rejects the action with HTTP 400 when those
    keys appear (microversion older than the one that introduced them).
    """
    rec = _Recorder().install(setup)

    result = invoke(["volume", "upload-to-image", VOL_ID, "img"])

    assert result.exit_code == 0, result.output
    payload = next(b for u, b in rec.posts if "/action" in u)["os-volume_upload_image"]
    assert "visibility" not in payload
    assert "protected" not in payload


def test_explicit_visibility_is_forwarded(invoke, setup):
    rec = _Recorder().install(setup)

    result = invoke([
        "volume", "upload-to-image", VOL_ID, "img",
        "--visibility", "shared",
    ])

    assert result.exit_code == 0, result.output
    payload = next(b for u, b in rec.posts if "/action" in u)["os-volume_upload_image"]
    assert payload["visibility"] == "shared"
    assert "protected" not in payload


def test_explicit_protected_is_forwarded(invoke, setup):
    rec = _Recorder().install(setup)

    result = invoke([
        "volume", "upload-to-image", VOL_ID, "img",
        "--protected",
    ])

    assert result.exit_code == 0, result.output
    payload = next(b for u, b in rec.posts if "/action" in u)["os-volume_upload_image"]
    assert payload["protected"] is True
    assert "visibility" not in payload


def test_strict_cinder_rejects_when_visibility_present(invoke, setup):
    """Simulate the Infomaniak-class 400 to prove the default path passes
    on a strict back-end and that explicit flags surface the error.
    """
    rec = _Recorder()

    def _strict_post(url, **kwargs):
        body = kwargs.get("json", {})
        rec.posts.append((url, body))
        if "/volumes/" in url and "/action" in url:
            inner = body.get("os-volume_upload_image", {})
            if "visibility" in inner or "protected" in inner:
                from orca_cli.core.exceptions import APIError
                raise APIError(
                    400,
                    "Additional properties are not allowed "
                    "('protected', 'visibility' were unexpected)",
                )
            return {
                "os-volume_upload_image": {
                    "id": VOL_ID, "image_id": IMG_ID, "status": "uploading",
                },
            }
        return {}

    setup.volume_url = "https://cinder.example.com/v3"
    setup.image_url = "https://glance.example.com"
    setup.get = lambda url, **kw: (
        {"volume": _vol()} if f"/volumes/{VOL_ID}" in url and "/action" not in url
        else {"volumes": []}
    )
    setup.post = _strict_post
    setup.patch = lambda url, **kw: _img()

    # Default invocation: must succeed.
    result_default = invoke(["volume", "upload-to-image", VOL_ID, "img"])
    assert result_default.exit_code == 0, result_default.output

    # Explicit visibility: must surface the strict back-end's 400.
    result_strict = invoke([
        "volume", "upload-to-image", VOL_ID, "img",
        "--visibility", "shared",
    ])
    assert result_strict.exit_code != 0
    out = result_strict.output + (result_strict.stderr_bytes or b"").decode(errors="replace")
    assert "400" in out


# ── name resolution ──────────────────────────────────────────────────────


def test_resolve_volume_by_name(invoke, setup):
    rec = _Recorder().install(setup)

    result = invoke(["volume", "upload-to-image", "src-vol", "img"])

    assert result.exit_code == 0, result.output
    # The POST URL must use the resolved UUID.
    action_posts = [u for u, _ in rec.posts if "/action" in u]
    assert action_posts, "expected one POST"
    assert VOL_ID in action_posts[0]
