"""Shell completion install helpers.

Used by both ``orca setup`` (offers auto-install at the end of the wizard)
and ``orca completion`` (dedicated command to install or print instructions).

Design — why a static-file install (ADR 0010):

The earlier install simply appended ``eval "$(_ORCA_COMPLETE=bash_source orca)"``
to the rc file. That line **regenerates the completion script on every shell
startup** by spawning ``orca``, which auto-walks ~60 command modules at import
time, then Click's ``_check_version()`` spawns the shell once more to detect
its version. Each login paid 1–3 s of wall time and could pile up under SSH
multiplexing or impatient retries.

The fix is the same pattern fish already uses: generate the completion script
**once** into a static file at install time, and have the rc just ``source``
that file. ``source`` of a 100-line bash file is microseconds; tab completion
itself still calls ``orca`` (via ``_ORCA_COMPLETE=bash_complete``), so the
lazy callbacks in ``orca_cli/core/completions.py`` keep working unchanged.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from orca_cli.core.exceptions import OrcaCLIError

_RC_FILE = {
    "bash": Path("~/.bashrc"),
    "zsh": Path("~/.zshrc"),
}
_FISH_COMPLETION_FILE = Path("~/.config/fish/completions/orca.fish")

SUPPORTED_SHELLS = ("bash", "zsh", "fish")

# Marker stripped on re-install / migration.
_RC_BLOCK_HEADER = "# orca-cli shell completion"

# Legacy install pattern we migrate away from on re-install (ADR 0010).
# Matches ``eval "$(_ORCA_COMPLETE=<shell>_source orca)"`` plus the optional
# preceding ``# orca-cli shell completion`` comment line.
_LEGACY_EVAL_RE = re.compile(
    r"(?:^[ \t]*#[ \t]*orca[\w \-]*completion[^\n]*\n)?"
    r"^[ \t]*eval[ \t]+\"\$\(\s*_ORCA_COMPLETE=\w+_source[ \t]+orca\s*\)\"[ \t]*\n",
    flags=re.MULTILINE,
)

# Marker stripped on re-install. Anchored so we only ever drop our own block.
_NEW_BLOCK_RE = re.compile(
    r"(?:^[ \t]*" + re.escape(_RC_BLOCK_HEADER) + r"[^\n]*\n)?"
    r"^[ \t]*(?:\[ -f [^\]]+\][ \t]+&&[ \t]+)?source[ \t]+[^\n]*orca[\w/.-]*completion\.[bz]a?sh[ \t]*\n",
    flags=re.MULTILINE,
)


def detect_shell() -> str | None:
    """Return ``bash``/``zsh``/``fish`` based on ``$SHELL``, or ``None``."""
    shell_env = os.environ.get("SHELL", "")
    if not shell_env:
        return None
    name = Path(shell_env).name
    return name if name in SUPPORTED_SHELLS else None


def _xdg_data_home() -> Path:
    """Return ``$XDG_DATA_HOME`` or ``~/.local/share`` per the XDG spec."""
    return Path(os.environ.get("XDG_DATA_HOME") or "~/.local/share").expanduser()


def _completion_script_path(shell: str) -> Path:
    """Where the static completion script lives on disk."""
    return _xdg_data_home() / "orca" / f"completion.{shell}"


def _generate_completion_script(shell: str) -> str:
    """Render the bash/zsh completion script by invoking ``orca`` once.

    We deliberately drive a subprocess instead of importing Click directly:
    the script we want is what users would see if they ran the eval at login,
    and that path goes through ``click.shell_completion`` end-to-end.
    """
    exe = shutil.which("orca")
    if not exe:
        raise OrcaCLIError(
            "orca not on PATH — cannot generate the completion script. "
            "Re-install orca-openstackclient or run 'orca completion show' "
            "for manual instructions.",
        )
    env = os.environ.copy()
    env["_ORCA_COMPLETE"] = f"{shell}_source"
    try:
        result = subprocess.run(
            [exe], env=env, capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OrcaCLIError(f"Failed to generate {shell} completion: {exc}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip() or "empty output"
        raise OrcaCLIError(f"Completion generation failed for {shell}: {detail}")
    return result.stdout


def install_completion_bashzsh(shell: str) -> str:
    """Install the static-script completion for bash or zsh.

    Generates ``$XDG_DATA_HOME/orca/completion.<shell>`` and ensures the rc
    file sources it. Strips any legacy ``eval "$(_ORCA_COMPLETE=...)"`` line
    on the way through, so re-running this command after upgrading from an
    older orca-cli silently migrates the user.
    """
    rc = _RC_FILE[shell].expanduser()
    script_path = _completion_script_path(shell)

    # Step 1: (re)generate the static script.
    script = _generate_completion_script(shell)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script)

    # Step 2: rewrite the rc so it sources the static script exactly once.
    # We always re-write our own block (idempotent) and migrate legacy eval.
    rc_content = rc.read_text() if rc.exists() else ""
    cleaned, n_legacy = _LEGACY_EVAL_RE.subn("", rc_content)
    cleaned, n_existing = _NEW_BLOCK_RE.subn("", cleaned)

    new_block = (
        f"{_RC_BLOCK_HEADER} (static script — see ADR 0010)\n"
        f'[ -f {script_path} ] && source {script_path}\n'
    )
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    cleaned = cleaned.rstrip("\n") + "\n\n" + new_block if cleaned else new_block

    rc.parent.mkdir(parents=True, exist_ok=True)
    rc.write_text(cleaned)

    if n_legacy:
        return (
            f"Migrated {rc} away from eager eval (it slowed every shell "
            f"startup). Wrote {script_path}. Open a new shell."
        )
    if n_existing:
        return f"Refreshed {script_path} and {rc}. Open a new shell."
    return f"Wrote {script_path} and added source line to {rc}. Open a new shell."


def install_completion_fish() -> str:
    """Generate the fish completion script via ``orca`` and write it to
    ``~/.config/fish/completions/orca.fish``.
    """
    target = _FISH_COMPLETION_FILE.expanduser()
    if target.exists() and "_ORCA_COMPLETE=" in target.read_text():
        return f"Already present at {target}."
    exe = shutil.which("orca")
    if not exe:
        return "orca not on PATH — run 'orca completion fish' for manual install."
    target.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["_ORCA_COMPLETE"] = "fish_source"
    try:
        result = subprocess.run(
            [exe], env=env, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"Failed to generate fish completion: {exc}"
    if result.returncode != 0 or not result.stdout.strip():
        return f"orca completion generation failed: {result.stderr.strip() or 'empty output'}"
    target.write_text(result.stdout)
    return f"Wrote {target}. Start a new fish session."


def install_completion(shell: str) -> str:
    """Install completion for ``shell``. Dispatches to the right helper."""
    if shell == "fish":
        return install_completion_fish()
    if shell in ("bash", "zsh"):
        return install_completion_bashzsh(shell)
    raise OrcaCLIError(f"Unsupported shell: {shell}")
