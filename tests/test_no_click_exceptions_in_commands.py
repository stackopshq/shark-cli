"""Ratchet test: command and core modules must raise ``OrcaCLIError``,
not the raw Click exception classes nor ``SystemExit``.

CLAUDE.md (l.113) requires every error surfaced to the user to subclass
``OrcaCLIError`` so ``main()`` can catch it on the central handler and
print a uniform red ``Error: ...`` line. Bare ``click.ClickException``
or ``click.UsageError`` falls through to the generic ``except
Exception`` clause and the user sees ``Unexpected error: ...`` — UX
broken. ``raise SystemExit(...)`` does the same, plus skips any cleanup
the central handler does.

The audit on 2026-04-27 surfaced 72 violations; they were migrated in
the same change. The 2026-04-28 audit surfaced 5 ``SystemExit`` plus 2
``ClickException`` in ``core/waiter.py`` that the previous regex
missed. This test now scans both ``commands/`` and ``core/`` and
forbids both patterns.

``main.py`` is the only place ``sys.exit`` is allowed (top-level
handler) — it is excluded from the scan.
"""

from __future__ import annotations

import re
from pathlib import Path

ORCA_CLI_DIR = Path(__file__).resolve().parents[1] / "orca_cli"
SCANNED_DIRS = (ORCA_CLI_DIR / "commands", ORCA_CLI_DIR / "core")
EXCLUDED_FILES = {"main.py"}

_FORBIDDEN = re.compile(
    r"\braise\s+(?:click\.(?:ClickException|UsageError)|SystemExit)\b",
)

def test_no_click_exceptions_raised_in_commands():
    """Walk every commands/core module and reject ``raise
    click.ClickException``, ``raise click.UsageError``, or
    ``raise SystemExit``. Use ``OrcaCLIError`` instead (or a plain
    ``return`` for graceful no-op exits).
    """
    offenders: list[tuple[str, int, str]] = []

    for scan_dir in SCANNED_DIRS:
        for path in sorted(scan_dir.glob("*.py")):
            if path.name in EXCLUDED_FILES:
                continue
            for lineno, line in enumerate(path.read_text().splitlines(), start=1):
                if _FORBIDDEN.search(line):
                    rel = path.relative_to(ORCA_CLI_DIR)
                    offenders.append((str(rel), lineno, line.strip()))

    assert not offenders, (
        "Module(s) raise raw Click exceptions or SystemExit — those bypass "
        "the central OrcaCLIError handler in main() and surface as "
        "'Unexpected error: ...' to the user. Replace with OrcaCLIError "
        "(from orca_cli.core.exceptions), or use a plain `return` for "
        "graceful no-op exits:\n"
        + "\n".join(f"  {fn}:{ln}  {src}" for fn, ln, src in offenders)
    )
