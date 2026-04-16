"""Tests for ``orca metric`` commands."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# ── Helpers ────────────────────────────────────────────────────────────────

METRIC_ID = "11112222-3333-4444-5555-666677778888"
RESOURCE_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _setup_mock(mock_client):
    mock_client.metric_url = "https://gnocchi.example.com"

    def _get(url, **kwargs):
        # Resource types
        if "/resource_type" in url and "/resource/" not in url:
            return [
                {"name": "generic", "attributes": {}},
                {"name": "instance", "attributes": {"flavor_id": {}}},
            ]
        # Resource detail
        if f"/resource/generic/{RESOURCE_ID}" in url:
            return {
                "id": RESOURCE_ID, "type": "generic",
                "original_resource_id": "orig-1",
                "project_id": "proj-1", "user_id": "user-1",
                "started_at": "2025-01-01T00:00:00", "ended_at": None,
                "revision_start": "2025-01-01", "revision_end": None,
                "metrics": {"cpu_util": METRIC_ID},
            }
        # Resource list
        if "/resource/generic" in url or "/resource/instance" in url:
            return [{
                "id": RESOURCE_ID, "type": "generic",
                "original_resource_id": "orig-1",
                "started_at": "2025-01-01T00:00:00",
                "metrics": {"cpu_util": METRIC_ID},
            }]
        # Metric detail
        if f"/metric/{METRIC_ID}/measures" in url:
            return [
                ["2025-01-01T00:00:00+00:00", 300.0, 42.5],
                ["2025-01-01T00:05:00+00:00", 300.0, 55.2],
            ]
        if f"/metric/{METRIC_ID}" in url:
            return {
                "id": METRIC_ID, "name": "cpu_util", "unit": "%",
                "resource_id": RESOURCE_ID,
                "archive_policy_name": "high",
                "created_by_user_id": "user-1",
                "archive_policy": {
                    "name": "high",
                    "definition": [
                        {"granularity": "0:05:00", "points": 8640, "timespan": "30 days"},
                    ],
                },
            }
        # Metric list
        if "/metric" in url and "/measures" not in url:
            return [{
                "id": METRIC_ID, "name": "cpu_util", "unit": "%",
                "archive_policy": {"name": "high"},
                "resource": {"id": RESOURCE_ID},
            }]
        # Archive policies
        if "/archive_policy" in url:
            return [{
                "name": "high", "back_window": 0,
                "aggregation_methods": ["mean", "max"],
                "definition": [{"granularity": "0:05:00", "points": 8640}],
            }]
        # Status
        if "/status" in url:
            return {"storage": {"summary": {"measures": 42, "metrics": 10}}}
        return {}

    mock_client.get = _get


# ══════════════════════════════════════════════════════════════════════════
#  resource-type-list
# ══════════════════════════════════════════════════════════════════════════


class TestResourceTypes:

    def test_resource_type_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "resource-type-list"])
        assert result.exit_code == 0
        assert "generic" in result.output
        assert "instance" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  resource-list / resource-show
# ══════════════════════════════════════════════════════════════════════════


class TestResources:

    def test_resource_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "resource-list"])
        assert result.exit_code == 0
        assert "generic" in result.output

    def test_resource_list_with_type(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "resource-list", "--type", "instance"])
        assert result.exit_code == 0

    def test_resource_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "resource-show", RESOURCE_ID])
        assert result.exit_code == 0
        assert "cpu_util" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  metric list / show
# ══════════════════════════════════════════════════════════════════════════


class TestMetrics:

    def test_metric_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "list"])
        assert result.exit_code == 0
        assert "cpu_util" in result.output

    def test_metric_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "show", METRIC_ID])
        assert result.exit_code == 0
        assert "cpu_util" in result.output
        assert "high" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  measures
# ══════════════════════════════════════════════════════════════════════════


class TestMeasures:

    def test_measures(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "measures", METRIC_ID])
        assert result.exit_code == 0
        assert "42.5" in result.output
        assert "55.2" in result.output

    def test_measures_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.metric_url = "https://gnocchi.example.com"
        mock_client.get = lambda url, **kw: [] if "/measures" in url else {}

        result = invoke(["metric", "measures", METRIC_ID])
        assert result.exit_code == 0
        assert "No measures found" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  archive-policy-list
# ══════════════════════════════════════════════════════════════════════════


class TestArchivePolicies:

    def test_archive_policy_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "archive-policy-list"])
        assert result.exit_code == 0
        assert "high" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  status
# ══════════════════════════════════════════════════════════════════════════


class TestMetricStatus:

    def test_status(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["metric", "status"])
        assert result.exit_code == 0
        assert "42" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  Help
# ══════════════════════════════════════════════════════════════════════════


class TestMetricHelp:

    def test_metric_help(self, invoke):
        result = invoke(["metric", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "measures", "resource-list",
                    "resource-show", "resource-type-list",
                    "archive-policy-list", "status"):
            assert cmd in result.output

    def test_measures_help(self, invoke):
        result = invoke(["metric", "measures", "--help"])
        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--granularity" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  metric create/delete / measures-add / archive-policy / resource-type
# ══════════════════════════════════════════════════════════════════════════

_GNOCCHI = "https://gnocchi.example.com"


class TestMetricCreate:

    def test_create(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        mock_client.post.return_value = {"id": METRIC_ID, "name": "cpu"}
        result = invoke(["metric", "create", "--name", "cpu",
                         "--archive-policy-name", "low"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "cpu"
        assert body["archive_policy_name"] == "low"

    def test_help(self, invoke):
        assert invoke(["metric", "create", "--help"]).exit_code == 0


class TestMetricDelete:

    def test_delete_yes(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "delete", METRIC_ID, "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "delete", METRIC_ID], input="n\n")
        assert result.exit_code != 0
        mock_client.delete.assert_not_called()

    def test_help(self, invoke):
        assert invoke(["metric", "delete", "--help"]).exit_code == 0


class TestMeasuresAdd:

    def test_add(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "measures-add", METRIC_ID,
                         "--measure", "2026-01-01T00:00:00:42.5"])
        assert result.exit_code == 0
        payload = mock_client.post.call_args[1]["json"]
        assert len(payload) == 1
        assert payload[0]["value"] == 42.5

    def test_add_invalid_format(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "measures-add", METRIC_ID,
                         "--measure", "badformat"])
        assert result.exit_code != 0

    def test_help(self, invoke):
        assert invoke(["metric", "measures-add", "--help"]).exit_code == 0


class TestArchivePolicy:

    def test_show(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        mock_client.get.return_value = {
            "name": "low", "definition": [], "aggregation_methods": ["mean"], "back_window": 0
        }
        result = invoke(["metric", "archive-policy-show", "low"])
        assert result.exit_code == 0
        assert "low" in result.output

    def test_create(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "archive-policy-create", "my-policy",
                         "--definition", "1m:1440",
                         "--definition", "1h:720"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "my-policy"
        assert len(body["definition"]) == 2

    def test_create_invalid_definition(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "archive-policy-create", "p",
                         "--definition", "bad"])
        assert result.exit_code != 0

    def test_delete_yes(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "archive-policy-delete", "my-policy", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_delete_requires_confirm(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "archive-policy-delete", "my-policy"], input="n\n")
        assert result.exit_code != 0

    def test_help_show(self, invoke):
        assert invoke(["metric", "archive-policy-show", "--help"]).exit_code == 0

    def test_help_create(self, invoke):
        assert invoke(["metric", "archive-policy-create", "--help"]).exit_code == 0


class TestResourceType:

    def test_show(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        mock_client.get.return_value = {"name": "instance", "attributes": {}}
        result = invoke(["metric", "resource-type-show", "instance"])
        assert result.exit_code == 0

    def test_create(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "resource-type-create", "my-type",
                         "--attribute", "host:string"])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body["name"] == "my-type"
        assert "host" in body["attributes"]

    def test_delete_yes(self, invoke, mock_client):
        mock_client.metric_url = _GNOCCHI
        result = invoke(["metric", "resource-type-delete", "my-type", "--yes"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_help_show(self, invoke):
        assert invoke(["metric", "resource-type-show", "--help"]).exit_code == 0

    def test_help_create(self, invoke):
        assert invoke(["metric", "resource-type-create", "--help"]).exit_code == 0
