"""Unit tests for ``orca_cli.services.image.ImageService``.

Focus: the surface that wasn't already covered by the command-level
tests in ``test_image*.py``: metadef catalogue, stream_download URL
helpers, _stream_put status-mapping, get_distro fallbacks.
Live e2e is in ``tests/devstack/test_live_image_full.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.core.exceptions import APIError, AuthenticationError, PermissionDeniedError
from orca_cli.services.image import ImageService

GLANCE = "https://glance.example.com/v2"


@pytest.fixture
def glance_client():
    client = MagicMock()
    client.image_url = GLANCE
    return client


@pytest.fixture
def svc(glance_client):
    return ImageService(glance_client)


def _resp(status_code: int = 201, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.is_success = 200 <= status_code < 300
    r.text = text
    return r


# ── _stream_put status mapping ─────────────────────────────────────────

def test_stream_put_success(glance_client, svc):
    glance_client.put_stream.return_value = _resp(204)
    # No raise, no return — just a sanity round-trip.
    svc._stream_put(f"{GLANCE}/images/i1/file", content=b"x", content_length=1)
    glance_client.put_stream.assert_called_once()


def test_stream_put_401_raises_authentication_error(glance_client, svc):
    glance_client.put_stream.return_value = _resp(401)
    with pytest.raises(AuthenticationError):
        svc._stream_put(f"{GLANCE}/images/i1/file", content=b"x", content_length=1)


def test_stream_put_403_raises_permission_denied(glance_client, svc):
    glance_client.put_stream.return_value = _resp(403)
    with pytest.raises(PermissionDeniedError):
        svc._stream_put(f"{GLANCE}/images/i1/file", content=b"x", content_length=1)


def test_stream_put_other_4xx_raises_api_error(glance_client, svc):
    glance_client.put_stream.return_value = _resp(413, text="too large")
    with pytest.raises(APIError):
        svc._stream_put(f"{GLANCE}/images/i1/file", content=b"x", content_length=1)


# ── URL helpers ────────────────────────────────────────────────────────

def test_download_url(svc):
    assert svc.download_url("img-1") == f"{GLANCE}/images/img-1/file"


def test_upload_url(svc):
    assert svc.upload_url("img-1") == f"{GLANCE}/images/img-1/file"


def test_stage_url(svc):
    assert svc.stage_url("img-1") == f"{GLANCE}/images/img-1/stage"


def test_stream_download_returns_get_stream_context(glance_client, svc):
    cm = MagicMock()
    glance_client.get_stream.return_value = cm
    out = svc.stream_download("img-1")
    glance_client.get_stream.assert_called_once_with(f"{GLANCE}/images/img-1/file")
    assert out is cm


# ── get_distro fallbacks ──────────────────────────────────────────────

def test_get_distro_lowercases(glance_client, svc):
    glance_client.get.return_value = {"os_distro": "Ubuntu"}
    assert svc.get_distro("img-1") == "ubuntu"


def test_get_distro_returns_empty_when_attr_missing(glance_client, svc):
    glance_client.get.return_value = {"name": "no-distro"}
    assert svc.get_distro("img-1") == ""


def test_get_distro_swallows_exception(glance_client, svc):
    glance_client.get.side_effect = APIError(500, "server down")
    assert svc.get_distro("img-1") == ""


# ── metadef: namespaces ───────────────────────────────────────────────

def test_find_metadef_namespaces(glance_client, svc):
    glance_client.get.return_value = {"namespaces": [{"namespace": "OS::Compute::Hypervisor"}]}
    out = svc.find_metadef_namespaces()
    glance_client.get.assert_called_once_with(f"{GLANCE}/metadefs/namespaces", params=None)
    assert out[0]["namespace"] == "OS::Compute::Hypervisor"


def test_find_metadef_namespaces_with_params(glance_client, svc):
    glance_client.get.return_value = {"namespaces": []}
    svc.find_metadef_namespaces(params={"resource_types": "OS::Glance::Image"})
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces",
        params={"resource_types": "OS::Glance::Image"},
    )


def test_get_metadef_namespace(glance_client, svc):
    glance_client.get.return_value = {"namespace": "OS::Compute::Quota"}
    svc.get_metadef_namespace("OS::Compute::Quota")
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/OS::Compute::Quota"
    )


def test_get_metadef_namespace_handles_none(glance_client, svc):
    glance_client.get.return_value = None
    assert svc.get_metadef_namespace("X") == {}


def test_create_metadef_namespace(glance_client, svc):
    glance_client.post.return_value = {"namespace": "ns1"}
    out = svc.create_metadef_namespace({"namespace": "ns1", "display_name": "NS"})
    glance_client.post.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces",
        json={"namespace": "ns1", "display_name": "NS"},
    )
    assert out["namespace"] == "ns1"


def test_create_metadef_namespace_handles_none(glance_client, svc):
    glance_client.post.return_value = None
    assert svc.create_metadef_namespace({}) == {}


def test_update_metadef_namespace(glance_client, svc):
    glance_client.put.return_value = {"namespace": "ns1", "visibility": "public"}
    out = svc.update_metadef_namespace("ns1", {"visibility": "public"})
    glance_client.put.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1",
        json={"visibility": "public"},
    )
    assert out["visibility"] == "public"


def test_update_metadef_namespace_handles_none(glance_client, svc):
    glance_client.put.return_value = None
    assert svc.update_metadef_namespace("ns1", {}) == {}


def test_delete_metadef_namespace(glance_client, svc):
    svc.delete_metadef_namespace("ns1")
    glance_client.delete.assert_called_once_with(f"{GLANCE}/metadefs/namespaces/ns1")


# ── metadef: objects ──────────────────────────────────────────────────

def test_find_metadef_objects(glance_client, svc):
    glance_client.get.return_value = {"objects": [{"name": "obj1"}]}
    out = svc.find_metadef_objects("ns1")
    glance_client.get.assert_called_once_with(f"{GLANCE}/metadefs/namespaces/ns1/objects")
    assert out[0]["name"] == "obj1"


def test_get_metadef_object(glance_client, svc):
    glance_client.get.return_value = {"name": "obj1"}
    out = svc.get_metadef_object("ns1", "obj1")
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/objects/obj1"
    )
    assert out["name"] == "obj1"


def test_get_metadef_object_handles_none(glance_client, svc):
    glance_client.get.return_value = None
    assert svc.get_metadef_object("ns1", "obj1") == {}


def test_create_metadef_object(glance_client, svc):
    glance_client.post.return_value = {"name": "obj1"}
    out = svc.create_metadef_object("ns1", {"name": "obj1", "properties": {}})
    glance_client.post.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/objects",
        json={"name": "obj1", "properties": {}},
    )
    assert out["name"] == "obj1"


def test_create_metadef_object_handles_none(glance_client, svc):
    glance_client.post.return_value = None
    assert svc.create_metadef_object("ns1", {}) == {}


def test_update_metadef_object(glance_client, svc):
    glance_client.put.return_value = {"name": "obj1", "description": "new"}
    out = svc.update_metadef_object("ns1", "obj1", {"description": "new"})
    glance_client.put.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/objects/obj1",
        json={"description": "new"},
    )
    assert out["description"] == "new"


def test_update_metadef_object_handles_none(glance_client, svc):
    glance_client.put.return_value = None
    assert svc.update_metadef_object("ns1", "obj1", {}) == {}


def test_delete_metadef_object(glance_client, svc):
    svc.delete_metadef_object("ns1", "obj1")
    glance_client.delete.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/objects/obj1"
    )


# ── metadef: properties (special parsing — Glance returns a dict) ─────

def test_find_metadef_properties_unwraps_dict_into_list(glance_client, svc):
    glance_client.get.return_value = {
        "properties": {
            "hw_disk_bus": {"type": "string", "title": "Disk Bus"},
            "hw_video_model": {"type": "string"},
        }
    }
    out = svc.find_metadef_properties("ns1")
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/properties"
    )
    names = sorted(p["name"] for p in out)
    assert names == ["hw_disk_bus", "hw_video_model"]
    # Each entry merges the inner dict back in.
    by_name = {p["name"]: p for p in out}
    assert by_name["hw_disk_bus"]["title"] == "Disk Bus"


def test_find_metadef_properties_accepts_list_shape(glance_client, svc):
    """Some servers / mocks return a list; the wrapper must tolerate it."""
    glance_client.get.return_value = {"properties": [{"name": "x"}]}
    out = svc.find_metadef_properties("ns1")
    assert out == [{"name": "x"}]


def test_find_metadef_properties_returns_empty_on_unexpected(glance_client, svc):
    glance_client.get.return_value = {"properties": 123}
    assert svc.find_metadef_properties("ns1") == []


def test_get_metadef_property(glance_client, svc):
    glance_client.get.return_value = {"name": "hw_disk_bus", "type": "string"}
    out = svc.get_metadef_property("ns1", "hw_disk_bus")
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/properties/hw_disk_bus"
    )
    assert out["type"] == "string"


def test_get_metadef_property_handles_none(glance_client, svc):
    glance_client.get.return_value = None
    assert svc.get_metadef_property("ns1", "x") == {}


def test_create_metadef_property(glance_client, svc):
    glance_client.post.return_value = {"name": "p1"}
    out = svc.create_metadef_property("ns1", {"name": "p1", "type": "integer"})
    glance_client.post.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/properties",
        json={"name": "p1", "type": "integer"},
    )
    assert out["name"] == "p1"


def test_create_metadef_property_handles_none(glance_client, svc):
    glance_client.post.return_value = None
    assert svc.create_metadef_property("ns1", {}) == {}


def test_update_metadef_property(glance_client, svc):
    glance_client.put.return_value = {"name": "p1", "title": "Updated"}
    out = svc.update_metadef_property("ns1", "p1", {"title": "Updated"})
    glance_client.put.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/properties/p1",
        json={"title": "Updated"},
    )
    assert out["title"] == "Updated"


def test_update_metadef_property_handles_none(glance_client, svc):
    glance_client.put.return_value = None
    assert svc.update_metadef_property("ns1", "p1", {}) == {}


def test_delete_metadef_property(glance_client, svc):
    svc.delete_metadef_property("ns1", "p1")
    glance_client.delete.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/properties/p1"
    )


# ── metadef: resource-type associations ──────────────────────────────

def test_find_metadef_resource_types(glance_client, svc):
    glance_client.get.return_value = {"resource_types": [{"name": "OS::Glance::Image"}]}
    out = svc.find_metadef_resource_types()
    glance_client.get.assert_called_once_with(f"{GLANCE}/metadefs/resource_types")
    assert out[0]["name"] == "OS::Glance::Image"


def test_find_metadef_resource_type_associations(glance_client, svc):
    glance_client.get.return_value = {
        "resource_type_associations": [{"name": "OS::Glance::Image"}]
    }
    out = svc.find_metadef_resource_type_associations("ns1")
    glance_client.get.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/resource_types"
    )
    assert out[0]["name"] == "OS::Glance::Image"


def test_create_metadef_resource_type_association(glance_client, svc):
    glance_client.post.return_value = {"name": "OS::Glance::Image"}
    out = svc.create_metadef_resource_type_association(
        "ns1", {"name": "OS::Glance::Image", "prefix": "hw_"}
    )
    glance_client.post.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/resource_types",
        json={"name": "OS::Glance::Image", "prefix": "hw_"},
    )
    assert out["name"] == "OS::Glance::Image"


def test_create_metadef_resource_type_association_handles_none(glance_client, svc):
    glance_client.post.return_value = None
    assert svc.create_metadef_resource_type_association("ns1", {}) == {}


def test_delete_metadef_resource_type_association(glance_client, svc):
    svc.delete_metadef_resource_type_association("ns1", "OS::Glance::Image")
    glance_client.delete.assert_called_once_with(
        f"{GLANCE}/metadefs/namespaces/ns1/resource_types/OS::Glance::Image"
    )
