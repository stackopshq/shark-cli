# ADR-0001: Lazy command registration

**Status**: Accepted
**Date**: 2026-04-20

## Context

orca exposes 65+ top-level commands grouped in `orca_cli/commands/`. The
original entry point eagerly imported every module via
`pkgutil.iter_modules`, then registered each module's top-level
`click.Command` objects on the root group. This kept `main.py` free of
hand-maintained import lists, but every invocation — even
`orca --version` — paid the import cost of the entire command tree
(httpx, yaml, every command module, every helper).

Measured cold-start before lazy loading: **~260 ms** for `orca --version`.

## Decision

The root group is a custom subclass `LazyOrcaGroup(click.Group)`. At
construction time it scans `orca_cli/commands/` for filenames (no
imports), builds a `command_name → module_name` index using the
convention `module_name.replace("_", "-")`, plus a small static
`_COMMAND_OVERRIDES` table for the five files that don't follow that
convention (`federation`, `limit`, `ip_whois`, `object_store`,
`qos_policy`).

`list_commands` returns the index keys; `get_command` imports exactly one
module on first call.

## Consequences

- **Positive**: any single-command invocation imports one command module
  instead of 65. Measured: `orca --version` 263 → 199 ms (-24 %),
  `orca server --help` 264 → 211 ms (-20 %).
- **Positive**: adding a new command is still "drop a file in
  `commands/`" — no bookkeeping in `main.py` unless the command name
  diverges from the filename or a single file exposes several commands
  (then add an override).
- **Negative / trade-off**: `orca --help` still loads everything because
  Click calls `get_command` on each entry to render the short
  description. Acceptable: real invocations dominate.
- **Negative / trade-off**: a new module that breaks the naming
  convention without an override entry will silently be unreachable.
  Mitigated by `tests/test_cli_registration.py::test_all_commands_registered`
  which compares `list_commands` against an explicit expected list.
