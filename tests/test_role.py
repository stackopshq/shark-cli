"""Tests for ``orca role`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

ROLE_ID = "11112222-3333-4444-5555-666677778888"
ROLE_ID2 = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
USER_ID = "99998888-7777-6666-5555-444433332222"
PROJECT_ID = "abcdabcd-1234-5678-9abc-def012345678"
DOMAIN_ID = "ddddeeee-ffff-0000-1111-222233334444"


def _role(role_id=ROLE_ID, name="my-role"):
    return {"id": role_id, "name": name, "description": "test role",
            "domain_id": None}


def _setup_mock(mock_client):
    mock_client.identity_url = "https://keystone.example.com:5000"

    patched = {}
    posted = {}
    deleted = []

    def _get(url, **kwargs):
        if f"/roles/{ROLE_ID}" in url:
            return {"role": _role()}
        if "/roles" in url:
            return {"roles": [_role(), _role(ROLE_ID2, "other-role")]}
        if "/role_assignments" in url:
            return {"role_assignments": [
                {"role": {"id": ROLE_ID}, "user": {"id": USER_ID},
                 "scope": {"project": {"id": PROJECT_ID}}}
            ]}
        return {}

    def _patch(url, **kwargs):
        body = kwargs.get("json", {})
        patched["last_body"] = body

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        return {}

    def _put(url, **kwargs):
        pass

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.patch = _patch
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"patched": patched, "posted": posted, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  role set
# ══════════════════════════════════════════════════════════════════════════


class TestRoleSet:

    def test_set_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "set", ROLE_ID, "--name", "new-name"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
        assert state["patched"]["last_body"]["role"]["name"] == "new-name"

    def test_set_description(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "set", ROLE_ID, "--description", "A new description"])
        assert result.exit_code == 0
        assert state["patched"]["last_body"]["role"]["description"] == "A new description"

    def test_set_name_and_description(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "set", ROLE_ID, "--name", "new-name",
                         "--description", "desc"])
        assert result.exit_code == 0
        body = state["patched"]["last_body"]["role"]
        assert body["name"] == "new-name"
        assert body["description"] == "desc"

    def test_set_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "set", ROLE_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestRoleHelp:

    def test_role_help(self, invoke):
        result = invoke(["role", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "add", "remove",
                    "assignment-list", "implied-list", "implied-create",
                    "implied-delete", "set"):
            assert cmd in result.output
