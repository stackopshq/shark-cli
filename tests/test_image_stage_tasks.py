"""Tests for ``orca image stage``, ``orca image stores-info``, and ``orca image task-*``."""

from __future__ import annotations

from unittest.mock import MagicMock

IMG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TASK_ID = "tttttttt-tttt-tttt-tttt-tttttttttttt"
GL = "https://glance.example.com"


def _setup(mock_client):
    mock_client.image_url = GL


# ══════════════════════════════════════════════════════════════════════════
#  image stage
# ══════════════════════════════════════════════════════════════════════════


class TestImageStage:

    def test_stage_calls_correct_url(self, invoke, mock_client, tmp_path):
        _setup(mock_client)
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"fake image data")

        put_calls = []

        def _put(url, **kwargs):
            put_calls.append(url)
            resp = MagicMock()
            resp.status_code = 204
            resp.is_success = True
            return resp

        mock_client._http.put = _put
        mock_client._headers = lambda: {"X-Auth-Token": "tok"}

        result = invoke(["image", "stage", IMG, str(img_file)])
        assert result.exit_code == 0
        assert any(f"/v2/images/{IMG}/stage" in u for u in put_calls)
        assert "complete" in result.output.lower()

    def test_stage_shows_followup_hint(self, invoke, mock_client, tmp_path):
        _setup(mock_client)
        img_file = tmp_path / "disk.img"
        img_file.write_bytes(b"data")

        def _put(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 204
            resp.is_success = True
            return resp

        mock_client._http.put = _put
        mock_client._headers = lambda: {"X-Auth-Token": "tok"}

        result = invoke(["image", "stage", IMG, str(img_file)])
        assert result.exit_code == 0
        assert "glance-direct" in result.output

    def test_stage_help(self, invoke):
        result = invoke(["image", "stage", "--help"])
        assert result.exit_code == 0
        assert "staging" in result.output.lower()


# ══════════════════════════════════════════════════════════════════════════
#  image stores-info
# ══════════════════════════════════════════════════════════════════════════


class TestImageStoresInfo:

    def test_list_stores(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {
            "stores": [
                {"id": "ceph1", "description": "Primary Ceph", "is_default": True},
                {"id": "ceph2", "description": "Backup Ceph", "is_default": False},
            ]
        }
        result = invoke(["image", "stores-info"])
        assert result.exit_code == 0
        assert "ceph1" in result.output
        assert "ceph2" in result.output

    def test_default_store_marked(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {
            "stores": [
                {"id": "fast", "description": "Fast SSD", "is_default": True},
            ]
        }
        result = invoke(["image", "stores-info"])
        assert result.exit_code == 0
        assert "yes" in result.output

    def test_detail_flag_uses_detail_url(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"stores": []}
        invoke(["image", "stores-info", "--detail"])
        url = mock_client.get.call_args[0][0]
        assert "/detail" in url

    def test_empty_stores(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"stores": []}
        result = invoke(["image", "stores-info"])
        assert result.exit_code == 0
        assert "No stores found" in result.output

    def test_help(self, invoke):
        result = invoke(["image", "stores-info", "--help"])
        assert result.exit_code == 0
        assert "--detail" in result.output


# ══════════════════════════════════════════════════════════════════════════
#  image task-list
# ══════════════════════════════════════════════════════════════════════════


class TestImageTaskList:

    def test_list_tasks(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {
            "tasks": [
                {
                    "id": TASK_ID,
                    "type": "import",
                    "status": "success",
                    "owner_id": "proj-1",
                    "created_at": "2025-01-01T00:00:00Z",
                    "expires_at": "2025-01-08T00:00:00Z",
                }
            ]
        }
        result = invoke(["image", "task-list"])
        assert result.exit_code == 0
        assert "impo" in result.output   # "import" may be truncated to "impo…"
        assert "succ" in result.output   # "success" may be truncated to "succ…"

    def test_filter_by_type(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"tasks": []}
        invoke(["image", "task-list", "--type", "import"])
        _, kwargs = mock_client.get.call_args
        assert kwargs.get("params", {}).get("type") == "import"

    def test_filter_by_status(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"tasks": []}
        invoke(["image", "task-list", "--status", "pending"])
        _, kwargs = mock_client.get.call_args
        assert kwargs.get("params", {}).get("status") == "pending"

    def test_empty_tasks(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"tasks": []}
        result = invoke(["image", "task-list"])
        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_invalid_type(self, invoke, mock_client):
        result = invoke(["image", "task-list", "--type", "badtype"])
        assert result.exit_code != 0


# ══════════════════════════════════════════════════════════════════════════
#  image task-show
# ══════════════════════════════════════════════════════════════════════════


class TestImageTaskShow:

    def test_show_task(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {
            "id": TASK_ID,
            "type": "import",
            "status": "processing",
            "message": "",
            "owner_id": "proj-1",
            "input": {"import_from": "https://example.com/img.qcow2"},
            "result": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
            "expires_at": "2025-01-08T00:00:00Z",
        }
        result = invoke(["image", "task-show", TASK_ID])
        assert result.exit_code == 0
        assert "import" in result.output
        assert "processing" in result.output

    def test_show_calls_correct_url(self, invoke, mock_client):
        _setup(mock_client)
        mock_client.get.return_value = {"id": TASK_ID, "type": "import", "status": "success"}
        invoke(["image", "task-show", TASK_ID])
        url = mock_client.get.call_args[0][0]
        assert f"/v2/tasks/{TASK_ID}" in url

    def test_help(self, invoke):
        result = invoke(["image", "task-show", "--help"])
        assert result.exit_code == 0
