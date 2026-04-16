"""Tests for ``orca security-group`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

SG_ID = "11112222-3333-4444-5555-666677778888"
RULE_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _sg(sg_id=SG_ID, name="my-sg", rules=None):
    return {
        "id": sg_id, "name": name,
        "description": "test group",
        "security_group_rules": rules or [
            {"id": RULE_ID, "direction": "ingress", "ethertype": "IPv4",
             "protocol": "tcp", "port_range_min": 22, "port_range_max": 22,
             "remote_ip_prefix": "0.0.0.0/0", "remote_group_id": None},
        ],
    }


def _setup_mock(mock_client):
    mock_client.network_url = "https://neutron.example.com"

    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if f"security-groups/{SG_ID}" in url:
            return {"security_group": _sg()}
        if "/security-groups" in url:
            return {"security_groups": [_sg()]}
        if "/ports" in url:
            return {"ports": [
                {"id": "p1", "security_groups": [SG_ID]},
            ]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        if "/security-group-rules" in url:
            return {"security_group_rule": {"id": "new-rule"}}
        if "/security-groups" in url:
            return {"security_group": {"id": "new-sg", "name": "new",
                                       "security_group_rules": []}}
        return {}

    def _put(url, **kwargs):
        body = kwargs.get("json", {})
        put_data.update(body)

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_data": put_data, "deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════
#  list
# ══════════════════════════════════════════════════════════════════════════


class TestSGList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["security-group", "list"])
        assert result.exit_code == 0
        assert "my-sg" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.network_url = "https://neutron.example.com"
        mock_client.get = lambda url, **kw: {"security_groups": []}

        result = invoke(["security-group", "list"])
        assert result.exit_code == 0
        assert "No security groups found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  show
# ══════════════════════════════════════════════════════════════════════════


class TestSGShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["security-group", "show", SG_ID])
        assert result.exit_code == 0
        assert "my-sg" in result.output
        assert "ingress" in result.output

    def test_show_port_range(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["security-group", "show", SG_ID])
        assert result.exit_code == 0
        assert "22" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  create
# ══════════════════════════════════════════════════════════════════════════


class TestSGCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["security-group", "create", "web-sg"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["security_group"]["name"] == "web-sg"

    def test_create_with_description(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["security-group", "create", "web-sg", "--description", "Web SG"])
        assert result.exit_code == 0
        assert state["posted"]["security_group"]["description"] == "Web SG"


# ══════════════════════════════════════════════════════════════════════════
#  update
# ══════════════════════════════════════════════════════════════════════════


class TestSGUpdate:

    def test_update_name(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["security-group", "update", SG_ID, "--name", "renamed"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_nothing(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["security-group", "update", SG_ID])
        assert result.exit_code == 0
        assert "Nothing" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════════════════════


class TestSGDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["security-group", "delete", SG_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  rule-add
# ══════════════════════════════════════════════════════════════════════════


class TestSGRuleAdd:

    def test_rule_add(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["security-group", "rule-add", SG_ID,
                         "--direction", "ingress", "--protocol", "tcp",
                         "--port-min", "80"])
        assert result.exit_code == 0
        assert "added" in result.output.lower()
        rule = state["posted"]["security_group_rule"]
        assert rule["protocol"] == "tcp"
        assert rule["port_range_min"] == 80

    def test_rule_add_with_remote_ip(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["security-group", "rule-add", SG_ID,
                         "--direction", "ingress", "--protocol", "tcp",
                         "--port-min", "443", "--remote-ip", "10.0.0.0/8"])
        assert result.exit_code == 0
        rule = state["posted"]["security_group_rule"]
        assert rule["remote_ip_prefix"] == "10.0.0.0/8"


# ══════════════════════════════════════════════════════════════════════════
#  rule-delete
# ══════════════════════════════════════════════════════════════════════════


class TestSGRuleDelete:

    def test_rule_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["security-group", "rule-delete", RULE_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  clone
# ══════════════════════════════════════════════════════════════════════════


class TestSGClone:

    def test_clone(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["security-group", "clone", SG_ID, "cloned-sg"])
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "cloned-sg" in result.output
        assert "1/1" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  cleanup
# ══════════════════════════════════════════════════════════════════════════


class TestSGCleanup:

    def test_cleanup_no_orphans(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)  # default: port p1 uses SG_ID

        result = invoke(["security-group", "cleanup"])
        assert result.exit_code == 0
        assert "No orphaned" in result.output

    def test_cleanup_with_orphans(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.network_url = "https://neutron.example.com"

        orphan_id = "22223333-4444-5555-6666-777788889999"

        def _get(url, **kwargs):
            if "/security-groups" in url:
                return {"security_groups": [
                    _sg(),
                    {"id": orphan_id, "name": "orphan-sg", "description": "",
                     "security_group_rules": []},
                ]}
            if "/ports" in url:
                return {"ports": [
                    {"id": "p1", "security_groups": [SG_ID]},
                ]}
            return {}

        mock_client.get = _get

        result = invoke(["security-group", "cleanup"])
        assert result.exit_code == 0
        assert "orphan" in result.output.lower()

    def test_cleanup_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.network_url = "https://neutron.example.com"

        orphan_id = "22223333-4444-5555-6666-777788889999"
        deleted = []

        def _get(url, **kwargs):
            if "/security-groups" in url:
                return {"security_groups": [
                    {"id": orphan_id, "name": "orphan-sg", "description": "",
                     "security_group_rules": []},
                ]}
            if "/ports" in url:
                return {"ports": []}
            return {}

        def _delete(url, **kwargs):
            deleted.append(url)

        mock_client.get = _get
        mock_client.delete = _delete

        result = invoke(["security-group", "cleanup", "--delete", "-y"])
        assert result.exit_code == 0
        assert len(deleted) == 1
        assert "1 deleted" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestSGHelp:

    def test_sg_help(self, invoke):
        result = invoke(["security-group", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "update", "delete",
                    "rule-add", "rule-delete", "clone", "cleanup"):
            assert cmd in result.output
