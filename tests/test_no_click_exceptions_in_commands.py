"""Ratchet test: command modules must raise ``OrcaCLIError``, not the
raw Click exception classes.

CLAUDE.md (l.113) requires every error surfaced to the user to subclass
``OrcaCLIError`` so ``main()`` can catch it on the central handler and
print a uniform red ``Error: ...`` line. Bare ``click.ClickException``
or ``click.UsageError`` falls through to the generic ``except
Exception`` clause and the user sees ``Unexpected error: ...`` — UX
broken.

The audit on 2026-04-27 surfaced 72 violations; they were migrated in
the same change. This test prevents new ones from creeping back in.
"""

from __future__ import annotations

import re
from pathlib import Path

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "orca_cli" / "commands"

_FORBIDDEN = re.compile(
    r"\braise\s+click\.(ClickException|UsageError)\b",
)


def test_no_click_exceptions_raised_in_commands():
    """Walk every commands module and reject ``raise click.ClickException``
    / ``raise click.UsageError``. Use ``OrcaCLIError`` instead.
    """
    offenders: list[tuple[str, int, str]] = []

    for path in sorted(COMMANDS_DIR.glob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            match = _FORBIDDEN.search(line)
            if match:
                offenders.append((path.name, lineno, line.strip()))

    assert not offenders, (
        "Command module(s) raise the raw Click exception classes — those "
        "bypass the central OrcaCLIError handler in main() and surface "
        "as 'Unexpected error: ...' to the user. Replace with "
        "OrcaCLIError (from orca_cli.core.exceptions):\n"
        + "\n".join(f"  {fn}:{ln}  {src}" for fn, ln, src in offenders)
    )
