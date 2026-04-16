"""Tests for ``orca alarm`` commands (Aodh)."""

from __future__ import annotations

import json

import pytest

# ── Constants ─────────────────────────────────────────────────────────────────

ALARM_ID   = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROJECT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
BASE       = "https://aodh.example.com"

_RULE = json.dumps({
    "metric": "cpu",
    "threshold": 70.0,
    "comparison_operator": "gt",
    "aggregation_method": "mean",
    "resource_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
    "resource_type": "instance",
    "granularity": 300,
    "evaluation_periods": 1,
})


def _aodh(mc):
    mc.alarming_url = BASE
    return mc


def _alarm(**kw):
    return {
        "alarm_id": ALARM_ID,
        "name": "cpu-high",
        "type": "gnocchi_resources_threshold",
        "state": "ok",
        "severity": "low",
        "enabled": True,
        "description": "",
        "project_id": PROJECT_ID,
        "user_id": "user-1",
        "repeat_actions": False,
        "alarm_actions": [],
        "ok_actions": [],
        "insufficient_data_actions": [],
        "gnocchi_resources_threshold_rule": json.loads(_RULE),
        "timestamp": "2026-01-01T00:00:00",
        "state_timestamp": "2026-01-01T00:00:00",
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  alarm list
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmList:

    def test_list(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = [_alarm()]
        result = invoke(["alarm", "list"])
        assert result.exit_code == 0
        assert "cpu-high" in result.output

    def test_list_empty(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        result = invoke(["alarm", "list"])
        assert "No alarms" in result.output

    def test_list_filter_type(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        invoke(["alarm", "list", "--type", "gnocchi_resources_threshold"])
        assert mock_client.get.call_args[1]["params"]["type"] == "gnocchi_resources_threshold"

    def test_list_filter_state(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        invoke(["alarm", "list", "--state", "alarm"])
        assert mock_client.get.call_args[1]["params"]["state"] == "alarm"

    def test_list_filter_name(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        invoke(["alarm", "list", "--name", "cpu"])
        assert mock_client.get.call_args[1]["params"]["name"] == "cpu"

    def test_list_limit(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        invoke(["alarm", "list", "--limit", "10"])
        assert mock_client.get.call_args[1]["params"]["limit"] == 10

    def test_help(self, invoke):
        assert invoke(["alarm", "list", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm show
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmShow:

    def test_show(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = _alarm()
        result = invoke(["alarm", "show", ALARM_ID])
        assert result.exit_code == 0
        assert "cpu-high" in result.output

    def test_help(self, invoke):
        assert invoke(["alarm", "show", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm create
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmCreate:

    def test_create_gnocchi_resources(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.post.return_value = _alarm()
        result = invoke(["alarm", "create",
                         "--name", "cpu-high",
                         "--type", "gnocchi_resources_threshold",
                         "--rule", _RULE])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "cpu-high"
        assert body["type"] == "gnocchi_resources_threshold"
        assert "gnocchi_resources_threshold_rule" in body
        assert body["gnocchi_resources_threshold_rule"]["threshold"] == 70.0

    def test_create_event(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.post.return_value = _alarm(type="event")
        rule = json.dumps({"event_type": "compute.instance.update"})
        result = invoke(["alarm", "create",
                         "--name", "instance-update",
                         "--type", "event",
                         "--rule", rule])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert "event_rule" in body

    def test_create_composite(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.post.return_value = _alarm(type="composite")
        rule = json.dumps({"operator": "and", "rules": []})
        result = invoke(["alarm", "create",
                         "--name", "composite-alarm",
                         "--type", "composite",
                         "--rule", rule])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert "composite_rule" in body

    def test_create_with_actions(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.post.return_value = _alarm()
        result = invoke(["alarm", "create",
                         "--name", "cpu-high",
                         "--type", "gnocchi_resources_threshold",
                         "--rule", _RULE,
                         "--alarm-action", "http://webhook.example.com/alarm",
                         "--ok-action", "http://webhook.example.com/ok"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert "http://webhook.example.com/alarm" in body["alarm_actions"]
        assert "http://webhook.example.com/ok" in body["ok_actions"]

    def test_create_invalid_rule_json(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "create",
                         "--name", "bad",
                         "--type", "event",
                         "--rule", "not-json"])
        assert result.exit_code != 0

    def test_create_severity(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.post.return_value = _alarm(severity="critical")
        invoke(["alarm", "create",
                "--name", "cpu-critical",
                "--type", "gnocchi_resources_threshold",
                "--rule", _RULE,
                "--severity", "critical"])
        body = mock_client.post.call_args[1]["json"]
        assert body["severity"] == "critical"

    def test_help(self, invoke):
        assert invoke(["alarm", "create", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm set
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmSet:

    def test_set_name(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = _alarm()
        result = invoke(["alarm", "set", ALARM_ID, "--name", "renamed"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body["name"] == "renamed"

    def test_set_rule(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = _alarm()
        new_rule = json.dumps({"threshold": 90.0, "comparison_operator": "gt",
                               "metric": "cpu", "aggregation_method": "mean",
                               "resource_id": "r", "resource_type": "instance",
                               "granularity": 60, "evaluation_periods": 1})
        result = invoke(["alarm", "set", ALARM_ID, "--rule", new_rule])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert "gnocchi_resources_threshold_rule" in body

    def test_set_nothing(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = _alarm()
        result = invoke(["alarm", "set", ALARM_ID])
        assert result.exit_code == 0
        mock_client.put.assert_not_called()

    def test_set_invalid_rule_json(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = _alarm()
        result = invoke(["alarm", "set", ALARM_ID, "--rule", "bad-json"])
        assert result.exit_code != 0

    def test_help(self, invoke):
        assert invoke(["alarm", "set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm delete
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmDelete:

    def test_delete_yes(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "delete", ALARM_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "delete", ALARM_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["alarm", "delete", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm state-get / state-set
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmState:

    def test_state_get_ok(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = '"ok"'
        result = invoke(["alarm", "state-get", ALARM_ID])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_state_get_alarm(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = "alarm"
        result = invoke(["alarm", "state-get", ALARM_ID])
        assert result.exit_code == 0
        assert "alarm" in result.output

    def test_state_set_ok(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "state-set", ALARM_ID, "ok"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        assert body == "ok"

    def test_state_set_alarm(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "state-set", ALARM_ID, "alarm"])
        assert result.exit_code == 0
        mock_client.put.assert_called_once()

    def test_state_set_invalid(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "state-set", ALARM_ID, "bad_state"])
        assert result.exit_code != 0

    def test_help_get(self, invoke):
        assert invoke(["alarm", "state-get", "--help"]).exit_code == 0

    def test_help_set(self, invoke):
        assert invoke(["alarm", "state-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm history
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmHistory:

    def test_history(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = [
            {"alarm_id": ALARM_ID, "type": "creation",
             "detail": '{"name": "cpu-high"}',
             "timestamp": "2026-01-01T00:00:00", "user_id": "user-1"},
            {"alarm_id": ALARM_ID, "type": "state_transition",
             "detail": '{"state": "alarm"}',
             "timestamp": "2026-01-02T00:00:00", "user_id": "user-1"},
        ]
        result = invoke(["alarm", "history", ALARM_ID])
        assert result.exit_code == 0
        assert "creation" in result.output

    def test_history_empty(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        result = invoke(["alarm", "history", ALARM_ID])
        assert "No history" in result.output

    def test_history_limit(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = []
        invoke(["alarm", "history", ALARM_ID, "--limit", "5"])
        assert mock_client.get.call_args[1]["params"]["limit"] == 5

    def test_help(self, invoke):
        assert invoke(["alarm", "history", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm capabilities
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmCapabilities:

    def test_capabilities(self, invoke, mock_client):
        _aodh(mock_client)
        mock_client.get.return_value = {
            "alarm_storage": {"gnocchi_resources_threshold": True},
        }
        result = invoke(["alarm", "capabilities"])
        assert result.exit_code == 0
        assert "gnocchi" in result.output

    def test_help(self, invoke):
        assert invoke(["alarm", "capabilities", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  alarm quota-set
# ══════════════════════════════════════════════════════════════════════════════

class TestAlarmQuotaSet:

    def test_quota_set(self, invoke, mock_client):
        _aodh(mock_client)
        result = invoke(["alarm", "quota-set", PROJECT_ID, "--alarms", "50"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["project_id"] == PROJECT_ID
        assert body["quotas"][0]["resource"] == "alarms"
        assert body["quotas"][0]["limit"] == 50

    def test_help(self, invoke):
        assert invoke(["alarm", "quota-set", "--help"]).exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.parametrize("sub", [
        "list", "show", "create", "set", "delete",
        "state-get", "state-set",
        "history", "capabilities", "quota-set",
    ])
    def test_subcommand_help(self, invoke, sub):
        assert invoke(["alarm", sub, "--help"]).exit_code == 0
