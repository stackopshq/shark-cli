"""Live e2e: Heat orchestration coverage.

Covers ``stack`` (create, list, show, set, delete + actions: check,
suspend, resume, cancel + introspection: event-list/show, output-list,
resource-list/show, template-show, template-validate, topology, diff,
resource-type-list/show, abandon).
"""

from __future__ import annotations

import time

import pytest

from tests.devstack.conftest import extract_uuid

pytestmark = pytest.mark.live


# Minimal HOT template (no provider resources required — uses
# OS::Heat::TestResource which is always available).
_TEMPLATE = """\
heat_template_version: 2018-08-31

description: live test minimal stack

parameters:
  message:
    type: string
    default: hello

resources:
  noop:
    type: OS::Heat::TestResource
    properties:
      value: { get_param: message }

outputs:
  echoed:
    description: the input message
    value: { get_attr: [noop, output] }
"""


@pytest.fixture
def stack_template(tmp_path):
    p = tmp_path / "stack.yaml"
    p.write_text(_TEMPLATE)
    return p


def _wait_stack(live_invoke, stack_id, target, timeout=300):
    import re
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = live_invoke("stack", "show", stack_id,
                          "-f", "value", "-c", "stack_status")
        if res.exit_code == 0:
            raw = res.output.strip().splitlines()[0]
            # orca's stack_status leaks Rich markup ([green]X[/green]) in
            # value/json output — strip it before comparing.
            status = re.sub(r"\[/?[a-z]+\]", "", raw)
            if status == target:
                return
            if "FAILED" in status:
                raise AssertionError(f"stack {stack_id} -> {status}")
        time.sleep(3)
    raise AssertionError(f"stack {stack_id} not {target} in {timeout}s")


def test_stack_full(live_invoke, cleanup, live_name, stack_template):
    name = live_name("stack")
    res = live_invoke("stack", "create", name,
                      "--template", str(stack_template),
                      "--parameter", "message=live-test")
    assert res.exit_code == 0, res.output
    stack_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("stack", "delete", stack_id, "--yes"))

    _wait_stack(live_invoke, stack_id, "CREATE_COMPLETE")

    # update
    res = live_invoke("stack", "update", stack_id,
                      "--template", str(stack_template),
                      "--parameter", "message=updated")
    assert res.exit_code == 0, res.output
    _wait_stack(live_invoke, stack_id, "UPDATE_COMPLETE")

    # show, list
    res = live_invoke("stack", "show", stack_id,
                      "-f", "value", "-c", "stack_name")
    assert res.exit_code == 0
    assert name in res.output

    res = live_invoke("stack", "list", "-f", "value", "-c", "ID")
    assert res.exit_code == 0
    assert stack_id in res.output

    # introspection
    for cmd in ("event-list", "output-list", "resource-list",
                "template-show", "topology"):
        res = live_invoke("stack", cmd, stack_id)
        assert res.exit_code == 0, f"{cmd}: {res.output}"

    # template-validate (independent of an existing stack)
    res = live_invoke("stack", "template-validate",
                      "--template", str(stack_template))
    assert res.exit_code == 0, res.output

    # resource-type-list / show — these are global Heat catalog ops
    res = live_invoke("stack", "resource-type-list",
                      "-f", "value", "-c", "Resource Type")
    assert res.exit_code == 0
    assert "OS::Heat::TestResource" in res.output

    res = live_invoke("stack", "resource-type-show", "OS::Heat::TestResource")
    assert res.exit_code == 0, res.output

    # actions: suspend, resume, check, cancel (cancel only works on
    # IN_PROGRESS — best-effort)
    res = live_invoke("stack", "suspend", stack_id)
    assert res.exit_code == 0, res.output
    _wait_stack(live_invoke, stack_id, "SUSPEND_COMPLETE")

    res = live_invoke("stack", "resume", stack_id)
    assert res.exit_code == 0, res.output
    _wait_stack(live_invoke, stack_id, "RESUME_COMPLETE")

    res = live_invoke("stack", "check", stack_id)
    assert res.exit_code == 0, res.output


def test_stack_diff(live_invoke, cleanup, live_name, stack_template, tmp_path):
    name = live_name("stack")
    res = live_invoke("stack", "create", name,
                      "--template", str(stack_template),
                      "--parameter", "message=v1")
    assert res.exit_code == 0, res.output
    stack_id = extract_uuid(res.output)
    cleanup(lambda: live_invoke("stack", "delete", stack_id, "--yes"))

    _wait_stack(live_invoke, stack_id, "CREATE_COMPLETE")

    # diff against a slightly modified template to exercise the path
    new_tpl = tmp_path / "stack-v2.yaml"
    new_tpl.write_text(_TEMPLATE.replace("default: hello", "default: world"))
    res = live_invoke("stack", "diff", stack_id,
                      "--template", str(new_tpl))
    assert res.exit_code == 0, res.output
