"""Ratchet test: command modules must not reach into ``client._*`` private
attributes or private helpers.

The full ADR-0007 migration is complete (v2.3.0): every command module
goes through a service in ``orca_cli/services/``. The service layer is
allowed to know about ``OrcaClient`` private surface (e.g. ``_request``,
``_handle_response``) — the *commands* are not.

Public alternatives are provided on ``OrcaClient``:

* ``client.token`` / ``client.token_data`` instead of the underscore form.
* ``client.catalog`` / ``client.auth_url`` / ``client.region_name`` /
  ``client.interface`` / ``client.project_id``.
* ``client.put_stream`` / ``client.post_stream`` / ``client.get_stream``
  / ``client.post_no_body`` / ``client.head_request`` for raw HTTP I/O.
* ``client.authenticate()`` to force a fresh round-trip.

When a new command needs something that is not on this list, add a
service method or a public client helper — do not reach past the
encapsulation.
"""

from __future__ import annotations

import re
from pathlib import Path

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "orca_cli" / "commands"

# Match ``client._foo`` where ``client`` is a local variable.
# Stripped: ``self._foo`` (services are allowed), ``cls._foo``, ``mock_client._foo``.
_PRIVATE_ACCESS = re.compile(r"\bclient\._[A-Za-z]")

def test_no_private_client_attribute_access_in_commands() -> None:
    """Walk every command module and reject ``client._<anything>`` access.

    Public properties / methods are listed in this test's docstring; if a
    new private bit is genuinely needed by a command, expose it on the
    client (or a service) and update the contract here.
    """
    offenders: list[tuple[str, int, str]] = []

    for path in sorted(COMMANDS_DIR.glob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if _PRIVATE_ACCESS.search(line):
                offenders.append((path.name, lineno, line.strip()))

    assert not offenders, (
        "Command module(s) reach into the private ``client._*`` surface. "
        "Use the public properties/helpers listed in this test's module "
        "docstring, or extend the service layer:\n"
        + "\n".join(f"  {fn}:{ln}  {src}" for fn, ln, src in offenders)
    )
