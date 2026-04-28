"""Unit tests for ``orca_cli.services.object_store.ObjectStoreService``.

Swift's mix of HEAD / POST-no-body / PUT-stream / GET-stream surfaces
makes URL/header shaping particularly easy to break. Lock it down at
unit-test speed; live e2e is in ``tests/devstack/test_live_object_store_full.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError
from orca_cli.services.object_store import ObjectStoreService

SWIFT = "https://swift.example.com/v1/AUTH_5678"

def _ok_resp(status_code: int = 200, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.headers = headers or {}
    resp.text = ""
    return resp

@pytest.fixture
def swift_client():
    client = MagicMock()
    client.object_store_url = SWIFT
    return client

@pytest.fixture
def svc(swift_client):
    return ObjectStoreService(swift_client)

# ── status mapping ─────────────────────────────────────────────────────

def test_head_account_maps_401_to_authentication_error(swift_client, svc):
    swift_client.head_request.return_value = _ok_resp(401)
    with pytest.raises(AuthenticationError):
        svc.head_account()

def test_head_account_maps_403_to_permission_denied(swift_client, svc):
    swift_client.head_request.return_value = _ok_resp(403)
    with pytest.raises(PermissionDeniedError):
        svc.head_account()

def test_head_account_maps_other_4xx_to_api_error(swift_client, svc):
    resp = _ok_resp(404)
    resp.text = "Account not found"
    swift_client.head_request.return_value = resp
    with pytest.raises(APIError) as exc:
        svc.head_account()
    assert "404" in str(exc.value) or "not found" in str(exc.value).lower()

# ── account ───────────────────────────────────────────────────────────

def test_head_account_returns_headers_as_dict(swift_client, svc):
    swift_client.head_request.return_value = _ok_resp(
        204, headers={"X-Account-Container-Count": "3", "X-Account-Bytes-Used": "100"}
    )
    out = svc.head_account()
    swift_client.head_request.assert_called_once_with(SWIFT)
    assert out["X-Account-Container-Count"] == "3"

def test_post_account_metadata_uses_post_no_body(swift_client, svc):
    swift_client.post_no_body.return_value = _ok_resp(204)
    svc.post_account_metadata({"X-Account-Meta-Owner": "alice"})
    swift_client.post_no_body.assert_called_once_with(
        SWIFT, extra_headers={"X-Account-Meta-Owner": "alice"}
    )

# ── containers ────────────────────────────────────────────────────────

def test_find_containers(swift_client, svc):
    swift_client.get.return_value = [{"name": "c1"}, {"name": "c2"}]
    out = svc.find_containers()
    swift_client.get.assert_called_once_with(f"{SWIFT}?format=json")
    assert [c["name"] for c in out] == ["c1", "c2"]

def test_find_containers_handles_unexpected_shape(swift_client, svc):
    swift_client.get.return_value = {"unexpected": "dict"}
    assert svc.find_containers() == []

def test_head_container(swift_client, svc):
    swift_client.head_request.return_value = _ok_resp(
        200, headers={"X-Container-Object-Count": "5"}
    )
    out = svc.head_container("c1")
    swift_client.head_request.assert_called_once_with(f"{SWIFT}/c1")
    assert out["X-Container-Object-Count"] == "5"

def test_create_container_puts_empty_stream(swift_client, svc):
    swift_client.put_stream.return_value = _ok_resp(201)
    svc.create_container("c1")
    args, kwargs = swift_client.put_stream.call_args
    assert args[0] == f"{SWIFT}/c1"
    assert kwargs["content"] == b""
    assert kwargs["content_length"] == 0

def test_create_container_passes_extra_headers(swift_client, svc):
    swift_client.put_stream.return_value = _ok_resp(201)
    svc.create_container("c1", headers={"X-Container-Read": ".r:*"})
    args, kwargs = swift_client.put_stream.call_args
    assert kwargs["extra_headers"] == {"X-Container-Read": ".r:*"}

def test_create_container_raises_on_failure(swift_client, svc):
    resp = _ok_resp(409)
    resp.text = "Conflict"
    swift_client.put_stream.return_value = resp
    with pytest.raises(APIError):
        svc.create_container("c1")

def test_delete_container(swift_client, svc):
    svc.delete_container("c1")
    swift_client.delete.assert_called_once_with(f"{SWIFT}/c1")

def test_post_container_metadata(swift_client, svc):
    swift_client.post_no_body.return_value = _ok_resp(204)
    svc.post_container_metadata("c1", {"X-Container-Meta-Owner": "bob"})
    swift_client.post_no_body.assert_called_once_with(
        f"{SWIFT}/c1", extra_headers={"X-Container-Meta-Owner": "bob"}
    )

# ── objects ───────────────────────────────────────────────────────────

def test_find_objects_basic(swift_client, svc):
    swift_client.get.return_value = [{"name": "o1"}]
    svc.find_objects("c1")
    swift_client.get.assert_called_once_with(f"{SWIFT}/c1?format=json")

def test_find_objects_with_prefix_and_delimiter(swift_client, svc):
    swift_client.get.return_value = []
    svc.find_objects("c1", prefix="dir/", delimiter="/")
    swift_client.get.assert_called_once_with(
        f"{SWIFT}/c1?format=json&prefix=dir/&delimiter=/"
    )

def test_find_objects_handles_dict_response(swift_client, svc):
    swift_client.get.return_value = {"unexpected": "dict"}
    assert svc.find_objects("c1") == []

def test_head_object(swift_client, svc):
    swift_client.head_request.return_value = _ok_resp(
        200, headers={"Content-Length": "42"}
    )
    out = svc.head_object("c1", "o1")
    swift_client.head_request.assert_called_once_with(f"{SWIFT}/c1/o1")
    assert out["Content-Length"] == "42"

def test_delete_object(swift_client, svc):
    svc.delete_object("c1", "o1")
    swift_client.delete.assert_called_once_with(f"{SWIFT}/c1/o1")

def test_post_object_metadata(swift_client, svc):
    swift_client.post_no_body.return_value = _ok_resp(202)
    svc.post_object_metadata("c1", "o1", {"X-Object-Meta-Tag": "draft"})
    swift_client.post_no_body.assert_called_once_with(
        f"{SWIFT}/c1/o1", extra_headers={"X-Object-Meta-Tag": "draft"}
    )

# ── streaming I/O ──────────────────────────────────────────────────────

def test_upload_object_default_args(swift_client, svc):
    swift_client.put_stream.return_value = _ok_resp(201)
    svc.upload_object("c1", "o1", content=b"hello")
    args, kwargs = swift_client.put_stream.call_args
    assert args[0] == f"{SWIFT}/c1/o1"
    assert kwargs["content"] == b"hello"
    assert kwargs["content_type"] == "application/octet-stream"
    assert kwargs["content_length"] is None

def test_upload_object_with_query(swift_client, svc):
    """SLO manifest uploads pass ?multipart-manifest=put."""
    swift_client.put_stream.return_value = _ok_resp(201)
    svc.upload_object(
        "c1", "manifest.json",
        content=b"[]", content_type="application/json", content_length=2,
        query="multipart-manifest=put",
    )
    args, kwargs = swift_client.put_stream.call_args
    assert args[0] == f"{SWIFT}/c1/manifest.json?multipart-manifest=put"
    assert kwargs["content_type"] == "application/json"
    assert kwargs["content_length"] == 2

def test_upload_object_raises_on_failure(swift_client, svc):
    swift_client.put_stream.return_value = _ok_resp(507)
    with pytest.raises(APIError):
        svc.upload_object("c1", "o1", content=b"")

def test_download_object_returns_stream_context(swift_client, svc):
    cm = MagicMock()
    swift_client.get_stream.return_value = cm
    out = svc.download_object("c1", "o1")
    swift_client.get_stream.assert_called_once_with(f"{SWIFT}/c1/o1")
    assert out is cm

def test_fetch_object_bytes_returns_content(swift_client, svc):
    resp = _ok_resp(200)
    resp.read = MagicMock()
    resp.content = b"hello world"
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    swift_client.get_stream.return_value = cm
    assert svc.fetch_object_bytes("c1", "o1") == b"hello world"

def test_fetch_object_bytes_raises_on_failure(swift_client, svc):
    resp = _ok_resp(403)
    resp.read = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    swift_client.get_stream.return_value = cm
    with pytest.raises(PermissionDeniedError):
        svc.fetch_object_bytes("c1", "o1")

def test_object_url_returns_canonical_path(svc):
    assert svc.object_url("c1", "path/to/o1") == f"{SWIFT}/c1/path/to/o1"
