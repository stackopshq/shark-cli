# ADR-0010: Static completion script for bash/zsh

**Status**: Accepted
**Date**: 2026-04-27

## Context

Up to and including v2.0.1, `orca completion install bash` (and the zsh
equivalent) appended a single line to the user's rc file:

```bash
eval "$(_ORCA_COMPLETE=bash_source orca)"
```

This is the canonical Click recipe and works correctly — it asks Click to
print the bash completion script on stdout, which `eval` then executes to
register the completion handler.

The cost is that **the eval re-runs every time the shell starts**:

- bash spawns `orca`
- `orca_cli/main.py` does an unconditional `pkgutil.iter_modules` over
  `orca_cli/commands/` (≈60 modules), each pulling in click, rich, httpx,
  the service layer, the typed models, …
- Click's `BashComplete.source()` then calls `_check_version()`, which
  spawns the shell once more (`subprocess.run(["bash", "--version"])`) to
  detect its version
- The generated script is printed and discarded

The wall-clock cost is 1–3 s per shell startup on a developer laptop, and
substantially worse under SSH multiplexing, slow disks, or when the user
hits Enter impatiently. A real incident on 2026-04-27 produced *hundreds*
of concurrent `orca` processes piled up on a single SSH login — every
process stuck inside `_check_version()` waiting on its `bash --version`
subprocess. The user-visible symptom was a login that hung for tens of
seconds, then dumped a multi-thousand-line traceback when the user
finally Ctrl-C'd.

## Decision

**Install bash/zsh completion the same way fish has always worked: as
a static script generated once at install time, sourced from the rc.**

The install command now:

1. Generates the completion script *once* by spawning
   `_ORCA_COMPLETE=<shell>_source orca` with the output captured.
2. Writes the script to `$XDG_DATA_HOME/orca/completion.<shell>`
   (`~/.local/share/orca/completion.<shell>` per the XDG Base Directory
   spec).
3. Rewrites the rc file so it sources that static file at login:

```bash
# orca-cli shell completion (static script — see ADR 0010)
[ -f ~/.local/share/orca/completion.bash ] && source ~/.local/share/orca/completion.bash
```

4. **Migrates** any pre-existing `eval "$(_ORCA_COMPLETE=...)"` line out
   of the rc as a side-effect, so a user upgrading from v2.0.x just
   re-runs `orca completion install bash` and is silently moved to the
   fast path. Surrounding rc content is preserved.

`source <file>` of a ≈100-line bash script is on the order of microseconds.
**No `orca` process is spawned at login** under this design.

## Consequences

### Positive

- **Login startup is no longer paying for orca import time.** The
  pile-up failure mode disappears outright — there is no orca process
  to pile up.
- The install is **idempotent and self-migrating**: re-running
  `orca completion install bash` on an old config moves the user to
  the new pattern without manual intervention.
- The pattern matches what fish already does, so the install layer is
  more uniform across shells.

### Negative

- **The static script goes stale when the orca command tree changes.**
  Adding/renaming a command requires regenerating the script — but
  Click's bash/zsh source script delegates the actual completion to
  `_ORCA_COMPLETE=<shell>_complete orca` at tab time, so what's frozen
  is only the registration glue, not the command list. In practice this
  has never been a problem for fish either.
- **Two files are now installed instead of one rc line.** Uninstall
  needs to remove both. Documented in the install message.

### Neutral

- The lazy completion callbacks in `orca_cli/core/completions.py` are
  unchanged. Tab completion still calls `orca` on demand to fetch
  resource IDs/names, with the same per-profile cache and 5-minute TTL
  introduced in v2.0.1.

## Alternatives considered

- **Optimise `orca`'s import path (lazy command registration).** Possible
  but the savings are bounded by Click+rich+httpx import cost (~250 ms
  on a warm cache, more on cold). Even at 100 ms per login this is not
  free, and it does nothing about Click's `_check_version()` subprocess.
- **Stop calling `_check_version()`.** Would require monkey-patching
  Click internals; brittle and breaks if Click changes the contract.
- **Precompile orca to a single binary (e.g. PyInstaller).** Solves the
  import cost but adds a release-engineering burden disproportionate to
  the problem and doesn't help users who installed via pip.

## Migration

Existing users on v2.0.1 or earlier:

```bash
# One command — detects the legacy eval line and replaces it.
orca completion install bash    # or zsh
exec $SHELL                     # pick up the new sourced file
```

If they prefer to do it by hand, the manual instructions printed by
`orca completion show bash` describe the same two-step flow.

## Related

- `orca_cli/core/shell_completion.py` — install logic.
- `orca_cli/commands/completion.py` — user-facing command and
  instructions.
- `tests/test_setup.py::TestInstallCompletionBashZsh` — covers the
  rewrite, the idempotency, and the legacy-eval migration.
