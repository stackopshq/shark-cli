"""Tests for ``orca backup`` commands (Freezer)."""

from __future__ import annotations

from orca_cli.core.config import save_profile, set_active_profile

# -- Helpers -----------------------------------------------------------------

BACKUP_ID = "bkp-abc123"
JOB_ID = "job-def456"
SESSION_ID = "sess-ghi789"
CLIENT_ID = "client-jkl012"
ACTION_ID = "act-mno345"


def _setup_mock(mock_client):
    mock_client.backup_url = "https://freezer.example.com"

    posted = {}
    put_urls = []
    deleted = []

    def _get(url, **kwargs):
        # Backups
        if f"/backups/{BACKUP_ID}" in url:
            return {
                "backup_id": BACKUP_ID, "backup_name": "my-backup",
                "container": "my-container", "status": "completed",
                "curr_backup_level": 0, "storage": "swift",
                "mode": "fs", "engine_name": "tar",
                "time_stamp": "2025-06-15T10:30:00",
                "path_to_backup": "/var/data", "hostname": "node1",
                "os_auth_version": "3", "project_id": "proj-1",
                "backup_metadata": {"extra_key": "extra_val"},
            }
        if "/backups" in url:
            return {"backups": [{
                "backup_id": BACKUP_ID, "backup_name": "my-backup",
                "container": "my-container", "curr_backup_level": 0,
                "status": "completed", "time_stamp": "2025-06-15T10:30:00",
            }]}

        # Jobs
        if f"/jobs/{JOB_ID}" in url and "/event" not in url:
            return {
                "job_id": JOB_ID, "description": "daily-backup",
                "client_id": CLIENT_ID, "user_id": "user-1",
                "project_id": "proj-1", "session_id": SESSION_ID,
                "job_schedule": {"status": "running", "event": "start", "time": ""},
                "job_actions": [{
                    "freezer_action": {
                        "action": "backup", "path_to_backup": "/var/data",
                        "container": "bkp-ct", "storage": "swift", "mode": "fs",
                    },
                }],
            }
        if "/jobs" in url:
            return {"jobs": [{
                "job_id": JOB_ID, "description": "daily-backup",
                "client_id": CLIENT_ID,
                "job_schedule": {"status": "running", "event": "start"},
                "job_actions": [{"freezer_action": {"action": "backup"}}],
            }]}

        # Sessions
        if f"/sessions/{SESSION_ID}" in url and "/action" not in url and "/jobs" not in url:
            return {
                "session_id": SESSION_ID, "description": "weekly-session",
                "status": "active", "user_id": "user-1",
                "project_id": "proj-1", "time_start": "2025-06-15T08:00:00",
                "time_end": "", "schedule": "7 days",
                "jobs": {JOB_ID: {"status": "completed"}},
            }
        if "/sessions" in url:
            return {"sessions": [{
                "session_id": SESSION_ID, "description": "weekly-session",
                "status": "active", "jobs": {JOB_ID: {}},
                "time_start": "2025-06-15T08:00:00", "time_end": "",
            }]}

        # Clients
        if f"/clients/{CLIENT_ID}" in url:
            return {
                "client_id": CLIENT_ID, "hostname": "node1",
                "description": "primary agent", "uuid": "uuid-abc",
                "user_id": "user-1", "project_id": "proj-1",
            }
        if "/clients" in url:
            return {"clients": [{
                "client_id": CLIENT_ID, "hostname": "node1",
                "description": "primary agent", "uuid": "uuid-abc",
            }]}

        # Actions
        if f"/actions/{ACTION_ID}" in url:
            return {
                "action_id": ACTION_ID, "user_id": "user-1",
                "project_id": "proj-1",
                "freezer_action": {
                    "action": "backup", "path_to_backup": "/var/data",
                    "container": "act-ct", "storage": "swift", "mode": "fs",
                    "engine_name": "tar", "backup_name": "nightly",
                },
            }
        if "/actions" in url:
            return {"actions": [{
                "action_id": ACTION_ID,
                "freezer_action": {
                    "action": "backup", "path_to_backup": "/var/data",
                    "storage": "swift", "mode": "fs",
                },
            }]}

        return {}

    def _post(url, **kwargs):
        body = kwargs.get("json", {})
        posted.update(body)
        if "/jobs" in url:
            return {"job_id": "new-job-id"}
        if "/sessions" in url:
            return {"session_id": "new-sess-id"}
        if "/clients" in url:
            return {"client_id": "new-client-id"}
        if "/actions" in url:
            return {"action_id": "new-action-id"}
        return {}

    def _put(url, **kwargs):
        put_urls.append(url)

    def _delete(url, **kwargs):
        deleted.append(url)

    mock_client.get = _get
    mock_client.post = _post
    mock_client.put = _put
    mock_client.delete = _delete

    return {"posted": posted, "put_urls": put_urls, "deleted": deleted}


# ============================================================================
#  backup list
# ============================================================================


class TestBackupList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "list"])
        assert result.exit_code == 0
        assert "my-b" in result.output
        assert "compl" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.backup_url = "https://freezer.example.com"
        mock_client.get = lambda url, **kw: {"backups": []}

        result = invoke(["backup", "list"])
        assert result.exit_code == 0
        assert "No backups found" in result.output


# ============================================================================
#  backup show
# ============================================================================


class TestBackupShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "show", BACKUP_ID])
        assert result.exit_code == 0
        assert "my-backup" in result.output
        assert "swift" in result.output
        assert "extra_val" in result.output


# ============================================================================
#  backup delete
# ============================================================================


class TestBackupDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "delete", BACKUP_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ============================================================================
#  backup job-list
# ============================================================================


class TestJobList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "job-list"])
        assert result.exit_code == 0
        assert "daily" in result.output
        assert "runn" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.backup_url = "https://freezer.example.com"
        mock_client.get = lambda url, **kw: {"jobs": []}

        result = invoke(["backup", "job-list"])
        assert result.exit_code == 0
        assert "No jobs found" in result.output


# ============================================================================
#  backup job-show
# ============================================================================


class TestJobShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "job-show", JOB_ID])
        assert result.exit_code == 0
        assert "daily" in result.output
        assert "backup" in result.output.lower()


# ============================================================================
#  backup job-create
# ============================================================================


class TestJobCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "job-create",
                         "--client-id", CLIENT_ID,
                         "--path", "/var/data",
                         "--container", "my-ct"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["client_id"] == CLIENT_ID
        assert state["posted"]["job_actions"][0]["freezer_action"]["path_to_backup"] == "/var/data"

    def test_create_restore(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "job-create",
                         "--client-id", CLIENT_ID,
                         "--path", "/var/restore",
                         "--action", "restore"])
        assert result.exit_code == 0
        fa = state["posted"]["job_actions"][0]["freezer_action"]
        assert fa["restore_abs_path"] == "/var/restore"
        assert fa["action"] == "restore"


# ============================================================================
#  backup job-start / job-stop
# ============================================================================


class TestJobStartStop:

    def test_start(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "job-start", JOB_ID])
        assert result.exit_code == 0
        assert "started" in result.output.lower()
        assert state["posted"]["event"] == "start"

    def test_stop(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "job-stop", JOB_ID])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()
        assert state["posted"]["event"] == "stop"


# ============================================================================
#  backup job-delete
# ============================================================================


class TestJobDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "job-delete", JOB_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ============================================================================
#  backup session-list
# ============================================================================


class TestSessionList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "session-list"])
        assert result.exit_code == 0
        assert "weekly" in result.output
        assert "activ" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.backup_url = "https://freezer.example.com"
        mock_client.get = lambda url, **kw: {"sessions": []}

        result = invoke(["backup", "session-list"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output


# ============================================================================
#  backup session-show
# ============================================================================


class TestSessionShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "session-show", SESSION_ID])
        assert result.exit_code == 0
        assert "weekly" in result.output
        assert "activ" in result.output


# ============================================================================
#  backup session-create
# ============================================================================


class TestSessionCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "session-create", "--description", "my-session"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        assert state["posted"]["description"] == "my-session"

    def test_create_with_schedule(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "session-create",
                         "--description", "sched-sess",
                         "--schedule-interval", "24 hours"])
        assert result.exit_code == 0
        assert state["posted"]["schedule"]["schedule_interval"] == "24 hours"


# ============================================================================
#  backup session-start
# ============================================================================


class TestSessionStart:

    def test_start(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _ = _setup_mock(mock_client)

        result = invoke(["backup", "session-start", SESSION_ID])
        assert result.exit_code == 0
        assert "started" in result.output.lower()


# ============================================================================
#  backup session-add-job / session-remove-job
# ============================================================================


class TestSessionAddRemoveJob:

    def test_add_job(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "session-add-job", SESSION_ID, JOB_ID])
        assert result.exit_code == 0
        assert "added" in result.output.lower()
        assert len(state["put_urls"]) == 1
        assert SESSION_ID in state["put_urls"][0]
        assert JOB_ID in state["put_urls"][0]

    def test_remove_job(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "session-remove-job", SESSION_ID, JOB_ID])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert len(state["deleted"]) == 1
        assert SESSION_ID in state["deleted"][0]


# ============================================================================
#  backup session-delete
# ============================================================================


class TestSessionDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "session-delete", SESSION_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ============================================================================
#  backup client-list
# ============================================================================


class TestClientList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "client-list"])
        assert result.exit_code == 0
        assert "node1" in result.output

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.backup_url = "https://freezer.example.com"
        mock_client.get = lambda url, **kw: {"clients": []}

        result = invoke(["backup", "client-list"])
        assert result.exit_code == 0
        assert "No clients found" in result.output


# ============================================================================
#  backup client-show
# ============================================================================


class TestClientShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "client-show", CLIENT_ID])
        assert result.exit_code == 0
        assert "node1" in result.output
        assert "primary" in result.output


# ============================================================================
#  backup client-register
# ============================================================================


class TestClientRegister:

    def test_register(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "client-register", "new-host",
                         "--description", "new agent"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower()
        assert state["posted"]["hostname"] == "new-host"


# ============================================================================
#  backup client-delete
# ============================================================================


class TestClientDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "client-delete", CLIENT_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ============================================================================
#  backup action-list
# ============================================================================


class TestActionList:

    def test_list(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "action-list"])
        assert result.exit_code == 0
        assert "backup" in result.output.lower()

    def test_list_empty(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        mock_client.backup_url = "https://freezer.example.com"
        mock_client.get = lambda url, **kw: {"actions": []}

        result = invoke(["backup", "action-list"])
        assert result.exit_code == 0
        assert "No actions found" in result.output


# ============================================================================
#  backup action-show
# ============================================================================


class TestActionShow:

    def test_show(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        _setup_mock(mock_client)

        result = invoke(["backup", "action-show", ACTION_ID])
        assert result.exit_code == 0
        assert "backup" in result.output.lower()
        assert "swift" in result.output


# ============================================================================
#  backup action-create
# ============================================================================


class TestActionCreate:

    def test_create(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "action-create",
                         "--path", "/var/data",
                         "--container", "act-ct"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()
        fa = state["posted"]["freezer_action"]
        assert fa["path_to_backup"] == "/var/data"
        assert fa["container"] == "act-ct"

    def test_create_restore(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "action-create",
                         "--action", "restore",
                         "--path", "/var/restore"])
        assert result.exit_code == 0
        fa = state["posted"]["freezer_action"]
        assert fa["restore_abs_path"] == "/var/restore"
        assert fa["action"] == "restore"


# ============================================================================
#  backup action-delete
# ============================================================================


class TestActionDelete:

    def test_delete(self, invoke, config_dir, mock_client, sample_profile):
        save_profile("p", sample_profile)
        set_active_profile("p")
        state = _setup_mock(mock_client)

        result = invoke(["backup", "action-delete", ACTION_ID, "-y"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        assert len(state["deleted"]) == 1


# ============================================================================
#  Help
# ============================================================================


class TestBackupHelp:

    def test_backup_help(self, invoke):
        result = invoke(["backup", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "delete",
                    "job-list", "job-show", "job-create", "job-start",
                    "job-stop", "job-delete",
                    "session-list", "session-show", "session-create",
                    "session-start", "session-add-job", "session-remove-job",
                    "session-delete",
                    "client-list", "client-show", "client-register",
                    "client-delete",
                    "action-list", "action-show", "action-create",
                    "action-delete"):
            assert cmd in result.output, f"'{cmd}' not in help output"
