"""Tests for ``orca event`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

SRV_ID = "12345678-1234-1234-1234-123456789abc"
REQ_ID = "req-aaaa-bbbb-cccc-dddd"


def _action(action="create", request_id=REQ_ID, start_time="2025-03-01T10:00:00Z",
            user_id="user-1", message="", events=None):
    return {
        "action": action,
        "request_id": request_id,
        "start_time": start_time,
        "user_id": user_id,
        "project_id": "proj-1",
        "message": message,
        "events": events or [],
    }


def _sub_event(event_name="compute_run_instance", result="Success",
               start_time="2025-03-01T10:00:00Z", finish_time="2025-03-01T10:00:05Z"):
    return {
        "event": event_name,
        "result": result,
        "start_time": start_time,
        "finish_time": finish_time,
    }


def _server(srv_id=SRV_ID, name="web-1", status="ACTIVE"):
    return {
        "id": srv_id, "name": name, "status": status,
        "security_groups": [{"name": "default"}],
    }


def _setup_mock(mock_client, actions=None, servers=None, action_detail=None):
    actions = actions or []
    servers = servers or []

    def _get(url, **kwargs):
        if "os-instance-actions/" in url:
            # Detail for a specific action
            return {"instanceAction": action_detail or (actions[0] if actions else _action())}
        if "os-instance-actions" in url:
            return {"instanceActions": actions}
        if "servers/detail" in url:
            return {"servers": servers}
        return {}

    mock_client.get = _get
    mock_client.compute_url = "https://nova.example.com/v2.1"


# ══════════════════════════════════════════════════════════════════════════
#  event list
# ══════════════════════════════════════════════════════════════════════════


class TestEventList:

    def test_list_actions(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, actions=[
            _action(action="create"),
            _action(action="stop", request_id="req-2", start_time="2025-03-02T10:00:00Z"),
        ])

        result = invoke(["event", "list", SRV_ID])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "stop" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, actions=[])

        result = invoke(["event", "list", SRV_ID])
        assert result.exit_code == 0
        assert "No instance actions found" in result.output

    def test_list_shows_request_id(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, actions=[_action()])

        result = invoke(["event", "list", SRV_ID])
        assert REQ_ID in result.output

    def test_list_shows_formatted_time(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, actions=[_action()])

        result = invoke(["event", "list", SRV_ID])
        assert "2025-03-01" in result.output
        assert "10:00:00" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  event show
# ══════════════════════════════════════════════════════════════════════════


class TestEventShow:

    def test_show_action(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, action_detail=_action(action="create"))

        result = invoke(["event", "show", SRV_ID, REQ_ID])
        assert result.exit_code == 0
        assert "create" in result.output
        assert REQ_ID in result.output

    def test_show_with_sub_events(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        detail = _action(action="create", events=[
            _sub_event("compute_run_instance", "Success"),
            _sub_event("network_setup", "Success",
                       start_time="2025-03-01T10:00:05Z",
                       finish_time="2025-03-01T10:00:08Z"),
        ])
        _setup_mock(mock_client, action_detail=detail)

        result = invoke(["event", "show", SRV_ID, REQ_ID])
        assert result.exit_code == 0
        assert "Sub-Events" in result.output
        # Rich may truncate long event names
        assert "compute_run_ins" in result.output
        assert "network_setup" in result.output
        assert "Success" in result.output

    def test_show_duration_displayed(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        detail = _action(events=[
            _sub_event(start_time="2025-03-01T10:00:00Z", finish_time="2025-03-01T10:00:05Z"),
        ])
        _setup_mock(mock_client, action_detail=detail)

        result = invoke(["event", "show", SRV_ID, REQ_ID])
        assert "5s" in result.output

    def test_show_no_sub_events(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, action_detail=_action(events=[]))

        result = invoke(["event", "show", SRV_ID, REQ_ID])
        assert result.exit_code == 0
        # No Sub-Events table
        assert "Sub-Events" not in result.output

    def test_show_error_result(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        detail = _action(events=[
            _sub_event(result="Error"),
        ])
        _setup_mock(mock_client, action_detail=detail)

        result = invoke(["event", "show", SRV_ID, REQ_ID])
        assert "Error" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  event all
# ══════════════════════════════════════════════════════════════════════════


class TestEventAll:

    def test_all_events(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        srv = _server()
        actions = [
            _action(action="create", start_time="2025-03-01T10:00:00Z"),
            _action(action="stop", request_id="req-2", start_time="2025-03-02T10:00:00Z"),
        ]

        def _get(url, **kwargs):
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            if "servers/detail" in url:
                return {"servers": [srv]}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "all"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "stop" in result.output
        assert "web-1" in result.output

    def test_all_with_action_filter(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        actions = [
            _action(action="create"),
            _action(action="stop", request_id="req-2"),
        ]

        def _get(url, **kwargs):
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            if "servers/detail" in url:
                return {"servers": [_server()]}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "all", "--action", "create"])
        assert result.exit_code == 0
        assert "create" in result.output

    def test_all_with_limit(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        actions = [_action(action="create", request_id=f"req-{i}",
                           start_time=f"2025-03-{i+1:02d}T10:00:00Z")
                   for i in range(10)]

        def _get(url, **kwargs):
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            if "servers/detail" in url:
                return {"servers": [_server()]}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "all", "--limit", "3"])
        assert result.exit_code == 0

    def test_all_no_servers(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        def _get(url, **kwargs):
            if "servers/detail" in url:
                return {"servers": []}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "all"])
        assert result.exit_code == 0
        assert "No instance actions found" in result.output

    def test_all_sorted_newest_first(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        actions = [
            _action(action="create", request_id="req-old", start_time="2025-01-01T10:00:00Z"),
            _action(action="stop", request_id="req-new", start_time="2025-06-01T10:00:00Z"),
        ]

        def _get(url, **kwargs):
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            if "servers/detail" in url:
                return {"servers": [_server()]}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "all"])
        # stop (newest) should come before create (oldest)
        stop_pos = result.output.index("stop")
        create_pos = result.output.index("create")
        assert stop_pos < create_pos


# ══════════════════════════════════════════════════════════════════════════
#  event timeline
# ══════════════════════════════════════════════════════════════════════════


class TestEventTimeline:

    def test_timeline_display(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        actions = [
            _action(action="create", start_time="2025-03-01T10:00:00Z"),
            _action(action="stop", request_id="req-2", start_time="2025-03-02T10:00:00Z"),
        ]
        detail = _action(action="create", events=[
            _sub_event("compute_run_instance", "Success"),
        ])

        def _get(url, **kwargs):
            if "os-instance-actions/" in url:
                return {"instanceAction": detail}
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "timeline", SRV_ID])
        assert result.exit_code == 0
        assert "Timeline" in result.output
        assert "create" in result.output
        assert "compute_run_instance" in result.output

    def test_timeline_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client, actions=[])

        result = invoke(["event", "timeline", SRV_ID])
        assert result.exit_code == 0
        assert "No instance actions found" in result.output

    def test_timeline_no_sub_events(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")

        actions = [_action(action="reboot")]
        detail = _action(action="reboot", events=[])

        def _get(url, **kwargs):
            if "os-instance-actions/" in url:
                return {"instanceAction": detail}
            if "os-instance-actions" in url:
                return {"instanceActions": actions}
            return {}

        mock_client.get = _get
        mock_client.compute_url = "https://nova.example.com/v2.1"

        result = invoke(["event", "timeline", SRV_ID])
        assert result.exit_code == 0
        assert "no sub-events" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestEventHelp:

    def test_event_help(self, invoke):
        result = invoke(["event", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "all", "timeline"):
            assert cmd in result.output

    def test_event_list_help(self, invoke):
        result = invoke(["event", "list", "--help"])
        assert result.exit_code == 0

    def test_event_all_help(self, invoke):
        result = invoke(["event", "all", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--action" in result.output
