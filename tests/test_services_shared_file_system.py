"""Unit tests for ``orca_cli.services.shared_file_system.FileShareService``.

Manila has no DevStack instance on the test bench, so this suite is
the primary safety net for URL/body shapes. Live e2e will follow
when a Manila-enabled cloud is available.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.services.shared_file_system import MANILA_MICROVERSION, FileShareService

MANILA = "https://share.example.com/v2"
MV_HEADER = {"X-OpenStack-Manila-API-Version": MANILA_MICROVERSION}


@pytest.fixture
def manila_client():
    client = MagicMock()
    client.share_url = MANILA
    return client


@pytest.fixture
def svc(manila_client):
    return FileShareService(manila_client)


# ── shares: CRUD ────────────────────────────────────────────────────────

def test_find_uses_detail_endpoint_by_default(manila_client, svc):
    manila_client.get.return_value = {"shares": [{"id": "s1"}]}
    out = svc.find()
    manila_client.get.assert_called_once_with(
        f"{MANILA}/shares/detail", params=None, headers=MV_HEADER,
    )
    assert out[0]["id"] == "s1"


def test_find_supports_summary_endpoint(manila_client, svc):
    manila_client.get.return_value = {"shares": []}
    svc.find(detail=False, params={"name": "foo"})
    manila_client.get.assert_called_once_with(
        f"{MANILA}/shares", params={"name": "foo"}, headers=MV_HEADER,
    )


def test_get_unwraps_share_envelope(manila_client, svc):
    manila_client.get.return_value = {"share": {"id": "s1", "size": 10}}
    out = svc.get("s1")
    manila_client.get.assert_called_once_with(
        f"{MANILA}/shares/s1", headers=MV_HEADER,
    )
    assert out["size"] == 10


def test_get_falls_back_when_no_envelope(manila_client, svc):
    manila_client.get.return_value = {"id": "raw"}
    assert svc.get("s1") == {"id": "raw"}


def test_create_wraps_body_under_share(manila_client, svc):
    manila_client.post.return_value = {"share": {"id": "new"}}
    out = svc.create({"name": "n", "size": 5, "share_proto": "NFS"})
    manila_client.post.assert_called_once_with(
        f"{MANILA}/shares",
        json={"share": {"name": "n", "size": 5, "share_proto": "NFS"}},
        headers=MV_HEADER,
    )
    assert out["id"] == "new"


def test_create_handles_none_response(manila_client, svc):
    manila_client.post.return_value = None
    assert svc.create({"name": "n"}) == {}


def test_update_wraps_body_under_share(manila_client, svc):
    manila_client.put.return_value = {"share": {"id": "s1", "name": "renamed"}}
    out = svc.update("s1", {"display_name": "renamed"})
    manila_client.put.assert_called_once_with(
        f"{MANILA}/shares/s1",
        json={"share": {"display_name": "renamed"}},
        headers=MV_HEADER,
    )
    assert out["name"] == "renamed"


def test_update_handles_none(manila_client, svc):
    manila_client.put.return_value = None
    assert svc.update("s1", {}) == {}


def test_delete(manila_client, svc):
    svc.delete("s1")
    manila_client.delete.assert_called_once_with(
        f"{MANILA}/shares/s1", headers=MV_HEADER,
    )


def test_extend_posts_action_with_new_size(manila_client, svc):
    svc.extend("s1", 20)
    manila_client.post.assert_called_once_with(
        f"{MANILA}/shares/s1/action",
        json={"extend": {"new_size": 20}}, headers=MV_HEADER,
    )


def test_shrink_posts_action_with_new_size(manila_client, svc):
    svc.shrink("s1", 5)
    manila_client.post.assert_called_once_with(
        f"{MANILA}/shares/s1/action",
        json={"shrink": {"new_size": 5}}, headers=MV_HEADER,
    )


# ── access rules ───────────────────────────────────────────────────────

def test_find_access_rules_filters_by_share_id(manila_client, svc):
    manila_client.get.return_value = {"access_list": [{"id": "a1"}]}
    out = svc.find_access_rules("s1")
    manila_client.get.assert_called_once_with(
        f"{MANILA}/share-access-rules",
        params={"share_id": "s1"}, headers=MV_HEADER,
    )
    assert out[0]["id"] == "a1"


def test_get_access_rule_unwraps(manila_client, svc):
    manila_client.get.return_value = {"access": {"id": "a1", "access_to": "10.0.0.1"}}
    out = svc.get_access_rule("a1")
    manila_client.get.assert_called_once_with(
        f"{MANILA}/share-access-rules/a1", headers=MV_HEADER,
    )
    assert out["access_to"] == "10.0.0.1"


def test_allow_access_minimal(manila_client, svc):
    manila_client.post.return_value = {"access": {"id": "a1"}}
    out = svc.allow_access("s1", "ip", "10.0.0.0/24")
    manila_client.post.assert_called_once_with(
        f"{MANILA}/shares/s1/action",
        json={"allow_access": {
            "access_type": "ip", "access_to": "10.0.0.0/24", "access_level": "rw",
        }},
        headers=MV_HEADER,
    )
    assert out["id"] == "a1"


def test_allow_access_with_ro_and_metadata(manila_client, svc):
    manila_client.post.return_value = {"access": {"id": "a1"}}
    svc.allow_access("s1", "user", "alice", access_level="ro",
                     metadata={"team": "ops"})
    body = manila_client.post.call_args.kwargs["json"]["allow_access"]
    assert body["access_level"] == "ro"
    assert body["metadata"] == {"team": "ops"}


def test_allow_access_handles_none(manila_client, svc):
    manila_client.post.return_value = None
    assert svc.allow_access("s1", "ip", "1.2.3.4") == {}


def test_deny_access_posts_action(manila_client, svc):
    svc.deny_access("s1", "a1")
    manila_client.post.assert_called_once_with(
        f"{MANILA}/shares/s1/action",
        json={"deny_access": {"access_id": "a1"}}, headers=MV_HEADER,
    )


# ── snapshots ──────────────────────────────────────────────────────────

def test_find_snapshots_detail(manila_client, svc):
    manila_client.get.return_value = {"snapshots": [{"id": "sn1"}]}
    out = svc.find_snapshots()
    manila_client.get.assert_called_once_with(
        f"{MANILA}/snapshots/detail", params=None, headers=MV_HEADER,
    )
    assert out[0]["id"] == "sn1"


def test_find_snapshots_summary(manila_client, svc):
    manila_client.get.return_value = {"snapshots": []}
    svc.find_snapshots(detail=False, params={"share_id": "s1"})
    manila_client.get.assert_called_once_with(
        f"{MANILA}/snapshots", params={"share_id": "s1"}, headers=MV_HEADER,
    )


def test_get_snapshot(manila_client, svc):
    manila_client.get.return_value = {"snapshot": {"id": "sn1"}}
    out = svc.get_snapshot("sn1")
    manila_client.get.assert_called_once_with(
        f"{MANILA}/snapshots/sn1", headers=MV_HEADER,
    )
    assert out["id"] == "sn1"


def test_create_snapshot_minimal(manila_client, svc):
    manila_client.post.return_value = {"snapshot": {"id": "sn1"}}
    svc.create_snapshot("s1")
    manila_client.post.assert_called_once_with(
        f"{MANILA}/snapshots",
        json={"snapshot": {"share_id": "s1"}}, headers=MV_HEADER,
    )


def test_create_snapshot_with_name_and_description(manila_client, svc):
    manila_client.post.return_value = {"snapshot": {"id": "sn1"}}
    svc.create_snapshot("s1", name="daily", description="nightly")
    body = manila_client.post.call_args.kwargs["json"]["snapshot"]
    assert body == {"share_id": "s1", "name": "daily", "description": "nightly"}


def test_create_snapshot_handles_none(manila_client, svc):
    manila_client.post.return_value = None
    assert svc.create_snapshot("s1") == {}


def test_delete_snapshot(manila_client, svc):
    svc.delete_snapshot("sn1")
    manila_client.delete.assert_called_once_with(
        f"{MANILA}/snapshots/sn1", headers=MV_HEADER,
    )


# ── types ─────────────────────────────────────────────────────────────

def test_find_types(manila_client, svc):
    manila_client.get.return_value = {"share_types": [{"id": "t1"}]}
    out = svc.find_types()
    manila_client.get.assert_called_once_with(
        f"{MANILA}/types", headers=MV_HEADER,
    )
    assert out[0]["id"] == "t1"


def test_get_type(manila_client, svc):
    manila_client.get.return_value = {"share_type": {"id": "t1", "name": "default"}}
    out = svc.get_type("t1")
    manila_client.get.assert_called_once_with(
        f"{MANILA}/types/t1", headers=MV_HEADER,
    )
    assert out["name"] == "default"
