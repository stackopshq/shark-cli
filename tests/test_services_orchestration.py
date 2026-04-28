"""Unit tests for ``orca_cli.services.orchestration.OrchestrationService``.

Each method is exercised by setting the mock client's HTTP method
return value, calling the service method, and asserting the right
URL/body/parsed return. Live e2e against Heat is covered separately
in ``tests/devstack/test_live_orchestration_full.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from orca_cli.services.orchestration import OrchestrationService

HEAT = "https://heat.example.com/v1/project-uuid-5678"


@pytest.fixture
def heat_client():
    client = MagicMock()
    client.orchestration_url = HEAT
    return client


@pytest.fixture
def svc(heat_client):
    return OrchestrationService(heat_client)


# ── stacks (CRUD) ────────────────────────────────────────────────────────

def test_find_returns_stacks_list(heat_client, svc):
    heat_client.get.return_value = {"stacks": [{"id": "s1"}, {"id": "s2"}]}
    out = svc.find()
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks", params=None, headers=None)
    assert [s["id"] for s in out] == ["s1", "s2"]


def test_find_passes_params_and_headers(heat_client, svc):
    heat_client.get.return_value = {"stacks": []}
    svc.find(params={"status": "COMPLETE"}, headers={"X": "1"})
    heat_client.get.assert_called_once_with(
        f"{HEAT}/stacks", params={"status": "COMPLETE"}, headers={"X": "1"}
    )


def test_find_all_paginates(heat_client, svc):
    heat_client.paginate.return_value = [{"id": "a"}, {"id": "b"}]
    out = svc.find_all(page_size=50, params={"q": "1"})
    heat_client.paginate.assert_called_once_with(
        f"{HEAT}/stacks", "stacks", page_size=50, params={"q": "1"}
    )
    assert len(out) == 2


def test_get_by_name_only_uses_canonical_url(heat_client, svc):
    heat_client.get.return_value = {"stack": {"id": "abc"}}
    out = svc.get("my-stack")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/my-stack")
    assert out == {"id": "abc"}


def test_get_with_stack_id_uses_canonical_path(heat_client, svc):
    heat_client.get.return_value = {"stack": {"id": "abc"}}
    svc.get("my-stack", "abc")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/my-stack/abc")


def test_get_unwraps_stack_envelope(heat_client, svc):
    heat_client.get.return_value = {"stack": {"id": "abc", "name": "my-stack"}}
    assert svc.get("my-stack")["name"] == "my-stack"


def test_get_falls_back_when_no_envelope(heat_client, svc):
    # Some Heat error shapes return a flat dict with no ``stack`` key.
    heat_client.get.return_value = {"id": "raw"}
    assert svc.get("x") == {"id": "raw"}


def test_create_posts_body_and_returns_stack(heat_client, svc):
    heat_client.post.return_value = {"stack": {"id": "new"}}
    out = svc.create({"stack_name": "n", "template": "t"})
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks", json={"stack_name": "n", "template": "t"}
    )
    assert out["id"] == "new"


def test_create_handles_empty_response(heat_client, svc):
    heat_client.post.return_value = None
    assert svc.create({"stack_name": "n"}) == {}


def test_update_calls_put(heat_client, svc):
    svc.update("n", "id-1", {"template": "t2"})
    heat_client.put.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1", json={"template": "t2"}
    )


def test_delete_calls_delete(heat_client, svc):
    svc.delete("n", "id-1")
    heat_client.delete.assert_called_once_with(f"{HEAT}/stacks/n/id-1")


def test_action_posts_to_actions_endpoint(heat_client, svc):
    heat_client.post.return_value = {}
    svc.action("n", "id-1", {"suspend": None})
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/actions", json={"suspend": None}
    )


def test_abandon_calls_delete_on_abandon(heat_client, svc):
    heat_client.delete.return_value = {"stack_data": "..."}
    out = svc.abandon("n", "id-1")
    heat_client.delete.assert_called_once_with(f"{HEAT}/stacks/n/id-1/abandon")
    assert "stack_data" in out


# ── resources & events ──────────────────────────────────────────────────

def test_find_resources_unwraps_envelope(heat_client, svc):
    heat_client.get.return_value = {"resources": [{"name": "r1"}]}
    out = svc.find_resources("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/resources")
    assert out[0]["name"] == "r1"


def test_get_resource_unwraps_envelope(heat_client, svc):
    heat_client.get.return_value = {"resource": {"name": "r1", "type": "T"}}
    out = svc.get_resource("n", "id-1", "r1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/resources/r1")
    assert out["type"] == "T"


def test_find_events_passes_params(heat_client, svc):
    heat_client.get.return_value = {"events": [{"id": "e1"}]}
    svc.find_events("n", "id-1", params={"limit": 50})
    heat_client.get.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/events", params={"limit": 50}
    )


def test_get_event_uses_long_path(heat_client, svc):
    heat_client.get.return_value = {"event": {"id": "e1"}}
    out = svc.get_event("n", "id-1", "r1", "e1")
    heat_client.get.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/resources/r1/events/e1"
    )
    assert out["id"] == "e1"


# ── outputs ────────────────────────────────────────────────────────────

def test_find_outputs(heat_client, svc):
    heat_client.get.return_value = {"outputs": [{"output_key": "k1"}]}
    out = svc.find_outputs("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/outputs")
    assert out[0]["output_key"] == "k1"


def test_get_output(heat_client, svc):
    heat_client.get.return_value = {"output": {"output_key": "k1", "output_value": "v"}}
    out = svc.get_output("n", "id-1", "k1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/outputs/k1")
    assert out["output_value"] == "v"


# ── templates / resource types ──────────────────────────────────────────

def test_get_template(heat_client, svc):
    heat_client.get.return_value = {"heat_template_version": "2018-08-31"}
    out = svc.get_template("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/template")
    assert "heat_template_version" in out


def test_validate_template_returns_dict(heat_client, svc):
    heat_client.post.return_value = {"Description": "ok"}
    out = svc.validate_template({"template": "..."})
    heat_client.post.assert_called_once_with(
        f"{HEAT}/validate", json={"template": "..."}
    )
    assert out == {"Description": "ok"}


def test_validate_template_handles_none(heat_client, svc):
    heat_client.post.return_value = None
    assert svc.validate_template({}) == {}


def test_find_resource_types(heat_client, svc):
    heat_client.get.return_value = {"resource_types": ["OS::Nova::Server"]}
    out = svc.find_resource_types(params={"name": "Server"})
    heat_client.get.assert_called_once_with(
        f"{HEAT}/resource_types", params={"name": "Server"}
    )
    assert out == ["OS::Nova::Server"]


def test_get_resource_type_template(heat_client, svc):
    heat_client.get.return_value = {"properties": {}}
    out = svc.get_resource_type_template("OS::Nova::Server",
                                          params={"template_type": "hot"})
    heat_client.get.assert_called_once_with(
        f"{HEAT}/resource_types/OS::Nova::Server/template",
        params={"template_type": "hot"},
    )
    assert out == {"properties": {}}


def test_get_resource_type_template_handles_none(heat_client, svc):
    heat_client.get.return_value = None
    assert svc.get_resource_type_template("X") == {}


# ── snapshots ──────────────────────────────────────────────────────────

def test_create_snapshot_without_name_sends_empty_body(heat_client, svc):
    heat_client.post.return_value = {"id": "snap1"}
    svc.create_snapshot("n", "id-1")
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/snapshots", json={}
    )


def test_create_snapshot_with_name_sets_name_in_body(heat_client, svc):
    heat_client.post.return_value = {"id": "snap1"}
    svc.create_snapshot("n", "id-1", "daily")
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/snapshots", json={"name": "daily"}
    )


def test_create_snapshot_returns_empty_on_none_response(heat_client, svc):
    heat_client.post.return_value = None
    assert svc.create_snapshot("n", "id-1") == {}


def test_find_snapshots(heat_client, svc):
    heat_client.get.return_value = {"snapshots": [{"id": "s1"}, {"id": "s2"}]}
    out = svc.find_snapshots("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/snapshots")
    assert [s["id"] for s in out] == ["s1", "s2"]


def test_find_snapshots_handles_unexpected_shape(heat_client, svc):
    heat_client.get.return_value = "not a dict"
    assert svc.find_snapshots("n", "id-1") == []


def test_get_snapshot_unwraps_envelope(heat_client, svc):
    heat_client.get.return_value = {"snapshot": {"id": "s1", "status": "COMPLETE"}}
    out = svc.get_snapshot("n", "id-1", "s1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/snapshots/s1")
    assert out["status"] == "COMPLETE"


def test_get_snapshot_returns_empty_on_unexpected_shape(heat_client, svc):
    heat_client.get.return_value = None
    assert svc.get_snapshot("n", "id-1", "s1") == {}


def test_delete_snapshot(heat_client, svc):
    svc.delete_snapshot("n", "id-1", "s1")
    heat_client.delete.assert_called_once_with(f"{HEAT}/stacks/n/id-1/snapshots/s1")


def test_restore_snapshot_posts_to_restore_endpoint(heat_client, svc):
    svc.restore_snapshot("n", "id-1", "s1")
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/snapshots/s1/restore"
    )


# ── adopt ──────────────────────────────────────────────────────────────

def test_adopt_posts_to_stacks(heat_client, svc):
    heat_client.post.return_value = {"stack": {"id": "new"}}
    out = svc.adopt({"stack_name": "n", "adopt_stack_data": "..."})
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks", json={"stack_name": "n", "adopt_stack_data": "..."}
    )
    assert out["id"] == "new"


def test_adopt_handles_none(heat_client, svc):
    heat_client.post.return_value = None
    assert svc.adopt({}) == {}


# ── files / environment / breakpoints ─────────────────────────────────

def test_get_files(heat_client, svc):
    heat_client.get.return_value = {"file1.yaml": "contents"}
    out = svc.get_files("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/files")
    assert out == {"file1.yaml": "contents"}


def test_get_files_handles_none(heat_client, svc):
    heat_client.get.return_value = None
    assert svc.get_files("n", "id-1") == {}


def test_get_environment(heat_client, svc):
    heat_client.get.return_value = {"resource_registry": {}}
    out = svc.get_environment("n", "id-1")
    heat_client.get.assert_called_once_with(f"{HEAT}/stacks/n/id-1/environment")
    assert "resource_registry" in out


def test_get_environment_handles_none(heat_client, svc):
    heat_client.get.return_value = None
    assert svc.get_environment("n", "id-1") == {}


# ── resource actions: signal / mark unhealthy / get metadata ───────────

def test_signal_resource_with_body(heat_client, svc):
    svc.signal_resource("n", "id-1", "r1", {"data": 42})
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/resources/r1/signal", json={"data": 42}
    )


def test_signal_resource_without_body_sends_empty(heat_client, svc):
    svc.signal_resource("n", "id-1", "r1")
    heat_client.post.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/resources/r1/signal", json={}
    )


def test_mark_resource_unhealthy_default_reason(heat_client, svc):
    svc.mark_resource_unhealthy("n", "id-1", "r1")
    heat_client.patch.assert_called_once()
    args, kwargs = heat_client.patch.call_args
    assert args[0] == f"{HEAT}/stacks/n/id-1/resources/r1"
    assert kwargs["json"]["mark_unhealthy"] is True
    assert "marked unhealthy via orca" in kwargs["json"]["resource_status_reason"]


def test_mark_resource_unhealthy_custom_reason(heat_client, svc):
    svc.mark_resource_unhealthy("n", "id-1", "r1", status_reason="manual override")
    args, kwargs = heat_client.patch.call_args
    assert kwargs["json"]["resource_status_reason"] == "manual override"


def test_get_resource_metadata_unwraps_envelope(heat_client, svc):
    heat_client.get.return_value = {"metadata": {"k": "v"}}
    out = svc.get_resource_metadata("n", "id-1", "r1")
    heat_client.get.assert_called_once_with(
        f"{HEAT}/stacks/n/id-1/resources/r1/metadata"
    )
    assert out == {"k": "v"}


def test_get_resource_metadata_handles_unexpected(heat_client, svc):
    heat_client.get.return_value = None
    assert svc.get_resource_metadata("n", "id-1", "r1") == {}
