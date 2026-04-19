"""Tests for ``orca rating`` commands (CloudKitty)."""

from __future__ import annotations

SERVICE_ID   = "11111111-1111-1111-1111-111111111111"
FIELD_ID     = "22222222-2222-2222-2222-222222222222"
MAPPING_ID   = "33333333-3333-3333-3333-333333333333"
THRESHOLD_ID = "44444444-4444-4444-4444-444444444444"
GROUP_ID     = "55555555-5555-5555-5555-555555555555"
BASE         = "https://cloudkitty.example.com"


def _rating(mc):
    mc.rating_url = BASE
    return mc


# ══════════════════════════════════════════════════════════════════════════════
#  rating info / metric-list / metric-show
# ══════════════════════════════════════════════════════════════════════════════

class TestInfoAndMetrics:

    def test_info(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"metrics": {"cpu": {"unit": "instance"}}}
        result = invoke(["rating", "info"])
        assert result.exit_code == 0
        assert "cpu" in result.output

    def test_metric_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"metrics": [
            {"metric_id": "instance_up", "unit": "instance", "metadata": ["flavor"]},
            {"metric_id": "volume.size", "unit": "GiB", "metadata": []},
        ]}
        result = invoke(["rating", "metric-list"])
        assert result.exit_code == 0
        assert "instance_up" in result.output
        assert "volume.size" in result.output

    def test_metric_show_uses_plural_path(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "metric_id": "instance_up", "unit": "instance", "metadata": ["flavor"]
        }
        result = invoke(["rating", "metric-show", "instance_up"])
        assert result.exit_code == 0
        # CloudKitty returns 405 on the singular /metric/{id} path.
        # The plural /metrics/{id} is the correct one.
        called_url = mock_client.get.call_args[0][0]
        assert called_url.endswith("/v1/info/metrics/instance_up")


# ══════════════════════════════════════════════════════════════════════════════
#  rating summary / dataframes / quote
# ══════════════════════════════════════════════════════════════════════════════

class TestSummary:

    def test_summary_default_window(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "total": 1,
            "columns": ["begin", "end", "qty", "rate"],
            "results": [["2026-04-01T00:00:00+00:00", "2026-04-19T00:00:00+00:00", 0.0, 0.0]],
        }
        result = invoke(["rating", "summary"])
        assert result.exit_code == 0
        assert "Begin" in result.output
        # Default window should pass begin+end params (start-of-month → now)
        params = mock_client.get.call_args[1]["params"]
        assert "begin" in params and "end" in params

    def test_summary_empty(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"total": 0, "columns": [], "results": []}
        result = invoke(["rating", "summary"])
        assert result.exit_code == 0
        assert "No rating data" in result.output

    def test_summary_groupby_and_filters(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"total": 0, "columns": [], "results": []}
        result = invoke([
            "rating", "summary",
            "--begin", "2026-04-01T00:00:00",
            "--end", "2026-04-30T00:00:00",
            "--groupby", "type", "--groupby", "project_id",
            "--filters", "project_id=abc123",
        ])
        assert result.exit_code == 0
        params = mock_client.get.call_args[1]["params"]
        assert params["groupby"] == ["type", "project_id"]
        assert params["filters[project_id]"] == "abc123"

    def test_summary_filters_missing_equals(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "summary", "--filters", "bad-filter"])
        assert result.exit_code != 0


class TestDataframes:

    def test_dataframes_v2(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"dataframes": [{"id": "d1"}]}
        result = invoke(["rating", "dataframes"])
        assert result.exit_code == 0
        assert "d1" in result.output

    def test_dataframes_v1_fallback(self, invoke, mock_client):
        _rating(mock_client)
        # First call (v2) raises; second (v1) succeeds.
        def side(url, **kw):
            if "/v2/dataframes" in url:
                raise RuntimeError("404 — endpoint not exposed")
            return {"dataframes": [{"id": "legacy"}]}
        mock_client.get.side_effect = side
        result = invoke(["rating", "dataframes"])
        assert result.exit_code == 0
        assert "legacy" in result.output
        # Verify both paths were tried
        urls = [call[0][0] for call in mock_client.get.call_args_list]
        assert any("/v2/dataframes" in u for u in urls)
        assert any("/v1/storage/dataframes" in u for u in urls)

    def test_dataframes_empty(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"dataframes": []}
        result = invoke(["rating", "dataframes"])
        assert result.exit_code == 0
        assert "No dataframes" in result.output


class TestQuote:

    def test_quote_single_resource(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = 0.05
        result = invoke([
            "rating", "quote",
            "--resource", '{"service":"instance_up","desc":{"flavor_name":"m1.small"},"volume":"1"}',
        ])
        assert result.exit_code == 0
        assert "0.05" in result.output
        body = mock_client.post.call_args[1]["json"]
        assert body["resources"][0]["service"] == "instance_up"

    def test_quote_invalid_json(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "quote", "--resource", "not-json"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════════
#  rating modules
# ══════════════════════════════════════════════════════════════════════════════

class TestModules:

    def test_module_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"modules": [
            {"module_id": "hashmap", "enabled": True, "priority": 1, "description": "HashMap"},
            {"module_id": "pyscripts", "enabled": False, "priority": 0, "description": "PyScripts"},
        ]}
        result = invoke(["rating", "module-list"])
        assert result.exit_code == 0
        assert "hashmap" in result.output
        assert "pyscripts" in result.output

    def test_module_enable_merges_current(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "module_id": "hashmap", "enabled": False,
            "priority": 1, "description": "HashMap",
        }
        result = invoke(["rating", "module-enable", "hashmap"])
        assert result.exit_code == 0
        body = mock_client.put.call_args[1]["json"]
        # CloudKitty PUT wants the full module representation minus module_id
        assert body["enabled"] is True
        assert body["priority"] == 1
        assert body["description"] == "HashMap"
        assert "module_id" not in body

    def test_module_disable(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "module_id": "hashmap", "enabled": True, "priority": 1, "description": ""
        }
        result = invoke(["rating", "module-disable", "hashmap"])
        assert result.exit_code == 0
        assert mock_client.put.call_args[1]["json"]["enabled"] is False

    def test_module_set_priority(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "module_id": "hashmap", "enabled": True, "priority": 1, "description": ""
        }
        result = invoke(["rating", "module-set-priority", "hashmap", "10"])
        assert result.exit_code == 0
        assert mock_client.put.call_args[1]["json"]["priority"] == 10


# ══════════════════════════════════════════════════════════════════════════════
#  rating hashmap
# ══════════════════════════════════════════════════════════════════════════════

class TestHashmapServices:

    def test_service_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"services": [
            {"service_id": SERVICE_ID, "name": "compute"},
        ]}
        result = invoke(["rating", "hashmap", "service-list"])
        assert result.exit_code == 0
        assert "compute" in result.output

    def test_service_create(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = {"service_id": SERVICE_ID, "name": "compute"}
        result = invoke(["rating", "hashmap", "service-create", "compute"])
        assert result.exit_code == 0
        assert mock_client.post.call_args[1]["json"] == {"name": "compute"}

    def test_service_delete(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "service-delete", SERVICE_ID, "-y"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
        assert SERVICE_ID in mock_client.delete.call_args[0][0]


class TestHashmapMappings:

    def test_mapping_create_requires_field_or_service(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "mapping-create", "--cost", "0.05"])
        assert result.exit_code != 0
        assert "--field-id or --service-id" in result.output

    def test_mapping_create_field_level(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = {"mapping_id": MAPPING_ID}
        result = invoke([
            "rating", "hashmap", "mapping-create",
            "--field-id", FIELD_ID, "--value", "m1.small",
            "--cost", "0.05",
        ])
        assert result.exit_code == 0
        body = mock_client.post.call_args[1]["json"]
        assert body == {
            "cost": "0.05", "type": "flat",
            "field_id": FIELD_ID, "value": "m1.small",
        }

    def test_mapping_delete(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "mapping-delete", MAPPING_ID, "-y"])
        assert result.exit_code == 0


class TestHashmapThresholds:

    def test_threshold_create_requires_field_or_service(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke([
            "rating", "hashmap", "threshold-create",
            "--level", "100", "--cost", "0.01",
        ])
        assert result.exit_code != 0

    def test_threshold_create(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = {"threshold_id": THRESHOLD_ID}
        result = invoke([
            "rating", "hashmap", "threshold-create",
            "--field-id", FIELD_ID, "--level", "100", "--cost", "0.01",
        ])
        assert result.exit_code == 0


class TestHashmapGroups:

    def test_group_create(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = {"group_id": GROUP_ID, "name": "premium"}
        result = invoke(["rating", "hashmap", "group-create", "premium"])
        assert result.exit_code == 0
        assert mock_client.post.call_args[1]["json"] == {"name": "premium"}

    def test_group_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"groups": [{"group_id": GROUP_ID, "name": "premium"}]}
        result = invoke(["rating", "hashmap", "group-list"])
        assert result.exit_code == 0
        assert "premium" in result.output

    def test_group_delete(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "group-delete", GROUP_ID, "-y"])
        assert result.exit_code == 0


class TestHashmapFieldsAndLists:

    def test_field_list_filtered(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"fields": [
            {"field_id": FIELD_ID, "name": "flavor_name", "service_id": SERVICE_ID},
        ]}
        result = invoke(["rating", "hashmap", "field-list", "--service-id", SERVICE_ID])
        assert result.exit_code == 0
        assert mock_client.get.call_args[1]["params"] == {"service_id": SERVICE_ID}

    def test_field_create(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.post.return_value = {"field_id": FIELD_ID}
        result = invoke(["rating", "hashmap", "field-create", SERVICE_ID, "flavor_name"])
        assert result.exit_code == 0
        assert mock_client.post.call_args[1]["json"] == {
            "service_id": SERVICE_ID, "name": "flavor_name",
        }

    def test_field_delete(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "field-delete", FIELD_ID, "-y"])
        assert result.exit_code == 0

    def test_mapping_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"mappings": [
            {"mapping_id": MAPPING_ID, "value": "m1.small", "cost": "0.05",
             "type": "flat", "field_id": FIELD_ID}
        ]}
        result = invoke(["rating", "hashmap", "mapping-list"])
        assert result.exit_code == 0
        assert "m1.small" in result.output

    def test_threshold_list(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {"thresholds": [
            {"threshold_id": THRESHOLD_ID, "level": "100", "cost": "0.01",
             "type": "flat", "field_id": FIELD_ID}
        ]}
        result = invoke(["rating", "hashmap", "threshold-list"])
        assert result.exit_code == 0

    def test_threshold_delete(self, invoke, mock_client):
        _rating(mock_client)
        result = invoke(["rating", "hashmap", "threshold-delete", THRESHOLD_ID, "-y"])
        assert result.exit_code == 0


class TestModuleShow:

    def test_module_show(self, invoke, mock_client):
        _rating(mock_client)
        mock_client.get.return_value = {
            "module_id": "hashmap", "enabled": True, "priority": 1,
            "description": "HashMap", "hot_config": True,
        }
        result = invoke(["rating", "module-show", "hashmap"])
        assert result.exit_code == 0
        assert "hashmap" in result.output.lower()
