"""Tests for `orca image member-*` (Glance image sharing)."""

from __future__ import annotations

import pytest

IMG_ID = "img-1111-1111-1111-111111111111"
PRJ_ID = "prj-2222-2222-2222-222222222222"


# ══════════════════════════════════════════════════════════════════════════
#  member-list
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberList:

    def test_list_members(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {
            "members": [
                {"member_id": PRJ_ID, "status": "accepted",
                 "created_at": "2024-01-01T00:00:00Z",
                 "updated_at": "2024-01-02T00:00:00Z",
                 "schema": "/v2/schemas/member"},
            ]
        }
        result = invoke(["image", "member-list", IMG_ID])
        assert result.exit_code == 0
        assert "prj-2222" in result.output  # Rich truncates long UUIDs
        assert "accepted" in result.output

    def test_list_empty(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"members": []}
        result = invoke(["image", "member-list", IMG_ID])
        assert result.exit_code == 0
        assert "No members" in result.output

    def test_list_calls_correct_url(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {"members": []}
        invoke(["image", "member-list", IMG_ID])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/images/{IMG_ID}/members" in url


# ══════════════════════════════════════════════════════════════════════════
#  member-create
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberCreate:

    def test_create(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.post.return_value = {
            "member_id": PRJ_ID, "status": "pending"
        }
        result = invoke(["image", "member-create", IMG_ID, PRJ_ID])
        assert result.exit_code == 0
        assert "pending" in result.output or "shared" in result.output

    def test_create_posts_correct_body(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.post.return_value = {"member_id": PRJ_ID, "status": "pending"}
        invoke(["image", "member-create", IMG_ID, PRJ_ID])
        body = mock_client.post.call_args[1]["json"]
        assert body["member"] == PRJ_ID

    def test_create_shows_acceptance_hint(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.post.return_value = {"member_id": PRJ_ID, "status": "pending"}
        result = invoke(["image", "member-create", IMG_ID, PRJ_ID])
        assert result.exit_code == 0
        assert "member-set" in result.output or "accept" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  member-delete
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberDelete:

    def test_delete(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        result = invoke(["image", "member-delete", IMG_ID, PRJ_ID, "--yes"])
        assert result.exit_code == 0
        assert "revoked" in result.output
        mock_client.delete.assert_called_once()

    def test_delete_calls_correct_url(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        result = invoke(["image", "member-delete", IMG_ID, PRJ_ID, "--yes"])
        assert result.exit_code == 0
        url = mock_client.delete.call_args[0][0]
        assert f"/v2/images/{IMG_ID}/members/{PRJ_ID}" in url


# ══════════════════════════════════════════════════════════════════════════
#  member-set
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberSet:

    @pytest.mark.parametrize("status", ["accepted", "rejected", "pending"])
    def test_set_status(self, invoke, mock_client, status):
        mock_client.image_url = "https://glance.example.com"
        result = invoke(["image", "member-set", IMG_ID, PRJ_ID, "--status", status])
        assert result.exit_code == 0
        assert status in result.output
        body = mock_client.put.call_args[1]["json"]
        assert body["status"] == status

    def test_set_calls_correct_url(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        invoke(["image", "member-set", IMG_ID, PRJ_ID, "--status", "accepted"])
        url = mock_client.put.call_args[0][0]
        assert f"/v2/images/{IMG_ID}/members/{PRJ_ID}" in url

    def test_invalid_status_rejected(self, invoke, mock_client):
        result = invoke(["image", "member-set", IMG_ID, PRJ_ID, "--status", "unknown"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  member-show
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberShow:

    def test_show_member(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {
            "image_id": IMG_ID,
            "member_id": PRJ_ID,
            "status": "accepted",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "schema": "/v2/schemas/member",
        }
        result = invoke(["image", "member-show", IMG_ID, PRJ_ID])
        assert result.exit_code == 0
        assert "accepted" in result.output
        assert "prj-2222" in result.output

    def test_show_calls_correct_url(self, invoke, mock_client):
        mock_client.image_url = "https://glance.example.com"
        mock_client.get.return_value = {
            "image_id": IMG_ID, "member_id": PRJ_ID, "status": "pending",
        }
        invoke(["image", "member-show", IMG_ID, PRJ_ID])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/images/{IMG_ID}/members/{PRJ_ID}" in url


# ══════════════════════════════════════════════════════════════════════════
#  --help checks
# ══════════════════════════════════════════════════════════════════════════

class TestImageMemberHelp:

    @pytest.mark.parametrize("sub", [
        "member-list", "member-show", "member-create", "member-delete", "member-set"
    ])
    def test_help(self, invoke, sub):
        result = invoke(["image", sub, "--help"])
        assert result.exit_code == 0
