"""Tests for identity commands (user, project, domain, role, group, application-credential)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Fixtures ───────────────────────────────────────────────────────────────

USER_ID   = "11112222-3333-4444-5555-666677778888"
PROJECT_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
DOMAIN_ID  = "dddd0000-1111-2222-3333-444455556666"
GROUP_ID   = "gggg0000-1111-2222-3333-444455556666"
ROLE_ID    = "rrrr0000-1111-2222-3333-444455556666"
CRED_ID    = "cccc0000-1111-2222-3333-444455556666"


def _user(uid=USER_ID):
    return {"id": uid, "name": "alice", "domain_id": DOMAIN_ID,
            "email": "alice@example.com", "enabled": True,
            "default_project_id": PROJECT_ID, "password_expires_at": None,
            "created_at": "2025-01-01", "updated_at": None}


def _project(pid=PROJECT_ID):
    return {"id": pid, "name": "my-project", "domain_id": DOMAIN_ID,
            "description": "A test project", "enabled": True, "parent_id": None, "tags": []}


def _domain(did=DOMAIN_ID):
    return {"id": did, "name": "my-domain", "description": "Test domain", "enabled": True}


def _group(gid=GROUP_ID):
    return {"id": gid, "name": "my-group", "domain_id": DOMAIN_ID, "description": "Test group"}


def _role(rid=ROLE_ID):
    return {"id": rid, "name": "member", "domain_id": None, "description": "Member role"}


def _appcred(cid=CRED_ID):
    return {"id": cid, "name": "my-cred", "description": "CI token",
            "project_id": PROJECT_ID, "expires_at": None,
            "unrestricted": False, "secret": "s3cr3t"}


def _setup_mock(mock_client):
    mock_client.identity_url = "https://keystone.example.com"
    mock_client._token_data = {"token": {"user": {"id": USER_ID}}}

    posted = {}
    patched = {}
    deleted = []
    put_urls = []

    def _get(url, **kwargs):
        if f"/users/{USER_ID}/application_credentials/{CRED_ID}" in url:
            return {"application_credential": _appcred()}
        if f"/users/{USER_ID}/application_credentials" in url:
            return {"application_credentials": [_appcred()]}
        if f"/users/{USER_ID}" in url:
            return {"user": _user()}
        if f"/groups/{GROUP_ID}/users" in url:
            return {"users": [_user()]}
        if f"/groups/{GROUP_ID}" in url:
            return {"group": _group()}
        if f"/projects/{PROJECT_ID}" in url:
            return {"project": _project()}
        if f"/domains/{DOMAIN_ID}" in url:
            return {"domain": _domain()}
        if f"/roles/{ROLE_ID}" in url:
            return {"role": _role()}
        if "/users" in url:
            return {"users": [_user()]}
        if "/projects" in url:
            return {"projects": [_project()]}
        if "/domains" in url:
            return {"domains": [_domain()]}
        if "/groups" in url:
            return {"groups": [_group()]}
        if "/roles" in url:
            return {"roles": [_role()]}
        if "/role_assignments" in url:
            return {"role_assignments": [{"role": {"id": ROLE_ID},
                    "user": {"id": USER_ID}, "group": {},
                    "scope": {"project": {"id": PROJECT_ID}}}]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        if "/application_credentials" in url:
            return {"application_credential": _appcred()}
        if "/users" in url:
            return {"user": _user()}
        if "/projects" in url:
            return {"project": _project()}
        if "/domains" in url:
            return {"domain": _domain()}
        if "/groups" in url:
            return {"group": _group()}
        if "/roles" in url:
            return {"role": _role()}
        return {}

    def _patch(url, **kwargs):
        patched["last_body"] = kwargs.get("json", {})

    def _put(url, **kwargs):
        put_urls.append(url)

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.patch = _patch
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "patched": patched, "deleted": deleted, "put_urls": put_urls}


# ══════════════════════════════════════════════════════════════════════════
#  Users
# ══════════════════════════════════════════════════════════════════════════


class TestUserList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["user", "list"])
        assert result.exit_code == 0
        assert "alice" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.identity_url = "https://keystone.example.com"
        mock_client.get = lambda url, **kw: {"users": []}

        result = invoke(["user", "list"])
        assert result.exit_code == 0
        assert "No users found" in result.output


class TestUserShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["user", "show", USER_ID])
        assert result.exit_code == 0
        assert "alice" in result.output


class TestUserCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["user", "create", "alice",
                         "--password", "secret", "--email", "alice@example.com"])
        assert result.exit_code == 0
        assert "created" in result.output


class TestUserUpdate:

    def test_update(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["user", "set", USER_ID, "--email", "new@example.com"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["user", "set", USER_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


class TestUserDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["user", "delete", USER_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output
        assert len(state["deleted"]) == 1


class TestUserSetPassword:

    def test_set_password(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["user", "set-password", USER_ID, "--password", "newpass"])
        assert result.exit_code == 0
        assert "Password updated" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Projects
# ══════════════════════════════════════════════════════════════════════════


class TestProjectList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["project", "list"])
        assert result.exit_code == 0
        assert "my-pro" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.identity_url = "https://keystone.example.com"
        mock_client.get = lambda url, **kw: {"projects": []}

        result = invoke(["project", "list"])
        assert result.exit_code == 0
        assert "No projects found" in result.output


class TestProjectShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["project", "show", PROJECT_ID])
        assert result.exit_code == 0
        assert "my-project" in result.output


class TestProjectCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["project", "create", "new-proj",
                         "--description", "A new project"])
        assert result.exit_code == 0
        assert "created" in result.output


class TestProjectUpdate:

    def test_update(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["project", "set", PROJECT_ID, "--name", "renamed"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["project", "set", PROJECT_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


class TestProjectDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["project", "delete", PROJECT_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Domains
# ══════════════════════════════════════════════════════════════════════════


class TestDomainList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["domain", "list"])
        assert result.exit_code == 0
        assert "my-domain" in result.output


class TestDomainShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["domain", "show", DOMAIN_ID])
        assert result.exit_code == 0
        assert "my-domain" in result.output


class TestDomainCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["domain", "create", "new-domain"])
        assert result.exit_code == 0
        assert "created" in result.output


class TestDomainUpdate:

    def test_update(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["domain", "set", DOMAIN_ID, "--name", "renamed"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["domain", "set", DOMAIN_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


class TestDomainDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["domain", "delete", DOMAIN_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Roles
# ══════════════════════════════════════════════════════════════════════════


class TestRoleList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "list"])
        assert result.exit_code == 0
        assert "member" in result.output


class TestRoleShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "show", ROLE_ID])
        assert result.exit_code == 0
        assert "member" in result.output


class TestRoleCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "create", "reader"])
        assert result.exit_code == 0
        assert "created" in result.output


class TestRoleDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "delete", ROLE_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


class TestRoleAdd:

    def test_add_to_project(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "add",
                         "--user", USER_ID, "--project", PROJECT_ID, ROLE_ID])
        assert result.exit_code == 0
        assert "granted" in result.output
        assert len(state["put_urls"]) == 1

    def test_remove_from_project(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["role", "remove",
                         "--user", USER_ID, "--project", PROJECT_ID, ROLE_ID])
        assert result.exit_code == 0
        assert "revoked" in result.output

    def test_add_missing_actor(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "add", "--project", PROJECT_ID, ROLE_ID])
        assert result.exit_code != 0

    def test_add_missing_scope(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "add", "--user", USER_ID, ROLE_ID])
        assert result.exit_code != 0


class TestRoleAssignmentList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["role", "assignment-list"])
        assert result.exit_code == 0
        assert ROLE_ID[:8] in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Groups
# ══════════════════════════════════════════════════════════════════════════


class TestGroupList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "list"])
        assert result.exit_code == 0
        assert "my-group" in result.output


class TestGroupShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "show", GROUP_ID])
        assert result.exit_code == 0
        assert "my-group" in result.output


class TestGroupCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "create", "devs"])
        assert result.exit_code == 0
        assert "created" in result.output


class TestGroupUpdate:

    def test_update(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "set", GROUP_ID, "--name", "engineers"])
        assert result.exit_code == 0
        assert "updated" in result.output

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "set", GROUP_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


class TestGroupDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["group", "delete", GROUP_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


class TestGroupUsers:

    def test_add_user(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["group", "add-user", GROUP_ID, USER_ID])
        assert result.exit_code == 0
        assert "added" in result.output
        assert len(state["put_urls"]) == 1

    def test_remove_user(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["group", "remove-user", GROUP_ID, USER_ID])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_user_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["group", "member-list", GROUP_ID])
        assert result.exit_code == 0
        assert "alice" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Application Credentials
# ══════════════════════════════════════════════════════════════════════════


class TestApplicationCredentials:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["application-credential", "list"])
        assert result.exit_code == 0
        assert "my-cred" in result.output

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["application-credential", "show", CRED_ID])
        assert result.exit_code == 0
        assert "my-cred" in result.output

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["application-credential", "create", "ci-token"])
        assert result.exit_code == 0
        assert "created" in result.output
        assert "s3cr3t" in result.output

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["application-credential", "delete", CRED_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestIdentityHelp:

    def test_user_help(self, invoke):
        result = invoke(["user", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete", "set-password"):
            assert cmd in result.output

    def test_project_help(self, invoke):
        result = invoke(["project", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete"):
            assert cmd in result.output

    def test_domain_help(self, invoke):
        result = invoke(["domain", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete"):
            assert cmd in result.output

    def test_role_help(self, invoke):
        result = invoke(["role", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete", "add", "remove", "assignment-list"):
            assert cmd in result.output

    def test_group_help(self, invoke):
        result = invoke(["group", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "set", "delete",
                    "add-user", "remove-user", "member-list"):
            assert cmd in result.output

    def test_application_credential_help(self, invoke):
        result = invoke(["application-credential", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "delete"):
            assert cmd in result.output
