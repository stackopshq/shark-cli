"""Tests for ``orca stack`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile


# ── Helpers ────────────────────────────────────────────────────────────────

STACK_ID = "11112222-3333-4444-5555-666677778888"


def _stack(stack_id=STACK_ID, name="my-stack", status="CREATE_COMPLETE"):
    return {
        "id": stack_id, "stack_name": name, "stack_status": status,
        "stack_status_reason": "Stack created", "description": "Test stack",
        "creation_time": "2025-01-01T00:00:00", "updated_time": None,
        "deletion_time": None, "timeout_mins": 60,
        "disable_rollback": True, "parent": None,
        "template_description": "A test template",
        "outputs": [{"output_key": "url", "output_value": "http://example.com"}],
        "parameters": {"param1": "value1"},
    }


def _setup_mock(mock_client):
    mock_client.orchestration_url = "https://heat.example.com/v1/proj"
    mock_client.compute_url = "https://nova.example.com/v2.1"

    posted = {}
    put_data = {}
    deleted = []

    def _get(url, **kwargs):
        if "/resources/" in url:
            return {"resource": {
                "resource_name": "my-server",
                "resource_type": "OS::Nova::Server",
                "resource_status": "CREATE_COMPLETE",
                "resource_status_reason": "Created",
                "physical_resource_id": "srv-1",
                "logical_resource_id": "my-server",
                "description": "", "creation_time": "2025-01-01",
                "updated_time": None, "attributes": {},
            }}
        if "/resources" in url:
            return {"resources": [{
                "resource_name": "my-server",
                "resource_type": "OS::Nova::Server",
                "resource_status": "CREATE_COMPLETE",
                "physical_resource_id": "srv-1",
            }]}
        if "/events/" in url:
            return {"event": {
                "id": "evt-1", "event_time": "2025-01-01T00:00:00",
                "resource_name": "my-server",
                "resource_status": "CREATE_COMPLETE",
                "resource_status_reason": "Created",
                "physical_resource_id": "srv-1",
                "logical_resource_id": "my-server",
                "resource_type": "OS::Nova::Server",
            }}
        if "/events" in url:
            return {"events": [{
                "id": "evt-1", "event_time": "2025-01-01T00:00:00",
                "resource_name": "my-server",
                "resource_status": "CREATE_COMPLETE",
                "resource_status_reason": "Created",
            }]}
        if "/outputs/" in url:
            return {"output": {
                "output_key": "url",
                "output_value": "http://example.com",
                "description": "Service URL",
            }}
        if "/outputs" in url:
            return {"outputs": [
                {"output_key": "url", "description": "Service URL"},
            ]}
        if "/template" in url:
            return {"heat_template_version": "2021-04-16",
                    "resources": {"server": {"type": "OS::Nova::Server"}}}
        if "/stacks/" in url or "/stacks/my-stack" in url:
            return {"stack": _stack()}
        if "/stacks" in url:
            return {"stacks": [_stack()]}
        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted["last_body"] = body
        if "/validate" in url:
            return {"Description": "Valid template", "Parameters": {}}
        if "/stacks" in url and "/actions" not in url:
            return {"stack": {"id": "new-stack"}}
        return {}

    def _put(url, **kwargs):
        body = kwargs.get("json", {})
        put_data["last_body"] = body

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_data": put_data, "deleted": deleted}


# ═══════════════════════════════════════════════════════════════════════��══
#  list
# ══════════════════════════════════════════════════════════════════════════


class TestStackList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "list"])
        assert result.exit_code == 0
        assert "my-st" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get = lambda url, **kw: {"stacks": []}

        result = invoke(["stack", "list"])
        assert result.exit_code == 0
        assert "No stacks found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  show
# ══════════════════════════════════════════════════════════════════════════


class TestStackShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "show", "my-stack"])
        assert result.exit_code == 0
        assert "my-stack" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  delete
# ══════════════════════════════════════════════════════════════════════════


class TestStackDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["stack", "delete", "my-stack", "-y"])
        assert result.exit_code == 0
        assert "deletion" in result.output.lower()
        assert len(state["deleted"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  actions: check, suspend, resume, cancel
# ══════════════════════════════════════════════════════════════════════════


class TestStackActions:

    def test_check(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "check", "my-stack"])
        assert result.exit_code == 0
        assert "Check" in result.output

    def test_suspend(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "suspend", "my-stack"])
        assert result.exit_code == 0
        assert "Suspend" in result.output

    def test_resume(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "resume", "my-stack"])
        assert result.exit_code == 0
        assert "Resume" in result.output

    def test_cancel(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "cancel", "my-stack"])
        assert result.exit_code == 0
        assert "Cancel" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  resource-list / resource-show
# ═════════════════════════════════════════════════════════════════════════��


class TestStackResources:

    def test_resource_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "resource-list", "my-stack"])
        assert result.exit_code == 0
        assert "my-ser" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  event-list
# ══════════════════════════════════════════════════════════════════════════


class TestStackEvents:

    def test_event_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "event-list", "my-stack"])
        assert result.exit_code == 0
        assert "my-ser" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  output-list / output-show
# ══════════════════════════════════════════════════════════════════════════


class TestStackOutputs:

    def test_output_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "output-list", "my-stack"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_output_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "output-show", "my-stack", "url"])
        assert result.exit_code == 0
        assert "example.com" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  template-show
# ══════════════════════════════════════════════════════════════════════════


class TestStackTemplate:

    def test_template_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "template-show", "my-stack"])
        assert result.exit_code == 0
        # Rich Syntax output — check for key terms
        assert "heat_template" in result.output or "Server" in result.output or "server" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  topology
# ══════════════════════════════════════════════════════════════════════════


class TestStackTopology:

    def test_topology(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["stack", "topology", "my-stack"])
        assert result.exit_code == 0
        assert "my-stack" in result.output
        assert "my-ser" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════


class TestHelpers:

    def test_status_style_complete(self):
        from orca_cli.commands.stack import _status_style
        assert _status_style("CREATE_COMPLETE") == "green"

    def test_status_style_failed(self):
        from orca_cli.commands.stack import _status_style
        assert _status_style("UPDATE_FAILED") == "red"

    def test_status_style_in_progress(self):
        from orca_cli.commands.stack import _status_style
        assert _status_style("CREATE_IN_PROGRESS") == "yellow"

    def test_parse_params(self):
        from orca_cli.commands.stack import _parse_params
        result = _parse_params(("key1=val1", "key2=val2"))
        assert result == {"key1": "val1", "key2": "val2"}

    def test_parse_params_invalid(self):
        import pytest
        from orca_cli.commands.stack import _parse_params
        with pytest.raises(Exception):
            _parse_params(("badformat",))


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestStackHelp:

    def test_stack_help(self, invoke):
        result = invoke(["stack", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "create", "update", "delete",
                    "check", "suspend", "resume", "cancel",
                    "resource-list", "resource-show",
                    "event-list", "event-show",
                    "output-list", "output-show",
                    "template-show", "template-validate",
                    "topology", "diff"):
            assert cmd in result.output


# ══════════════════════════════════════════════════════════════════════════
#  stack abandon / resource-type-list / resource-type-show
# ══════════════════════════════════════════════════════════════════════════

class TestStackAbandon:

    def test_abandon_yes(self, invoke, mock_client):
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get.return_value = {"stack": {"stack_name": "my-stack", "id": STACK_ID}}
        mock_client.delete.return_value = {"resources": {}}
        result = invoke(["stack", "abandon", "my-stack", "--yes"])
        assert result.exit_code == 0

    def test_abandon_requires_confirm(self, invoke, mock_client):
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get.return_value = {"stack": {"stack_name": "my-stack", "id": STACK_ID}}
        result = invoke(["stack", "abandon", "my-stack"], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["stack", "abandon", "--help"]).exit_code == 0


class TestStackResourceTypeList:

    def test_list(self, invoke, mock_client):
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get.return_value = {"resource_types": ["OS::Nova::Server", "OS::Neutron::Net"]}
        result = invoke(["stack", "resource-type-list"])
        assert result.exit_code == 0
        assert "Nova" in result.output

    def test_filter(self, invoke, mock_client):
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get.return_value = {"resource_types": []}
        invoke(["stack", "resource-type-list", "--filter", "Nova"])
        assert mock_client.get.call_args[1]["params"]["name"] == "Nova"

    def test_help(self, invoke):
        assert invoke(["stack", "resource-type-list", "--help"]).exit_code == 0


class TestStackResourceTypeShow:

    def test_show(self, invoke, mock_client):
        mock_client.orchestration_url = "https://heat.example.com/v1/proj"
        mock_client.get.return_value = {"heat_template_version": "2021-04-06"}
        result = invoke(["stack", "resource-type-show", "OS::Nova::Server"])
        assert result.exit_code == 0

    def test_help(self, invoke):
        assert invoke(["stack", "resource-type-show", "--help"]).exit_code == 0
