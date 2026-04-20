"""Shell completion install helpers.

Used by both ``orca setup`` (offers auto-install at the end of the wizard)
and ``orca completion`` (dedicated command to install or print instructions).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_COMPLETION_EVAL = {
    "bash": 'eval "$(_ORCA_COMPLETE=bash_source orca)"',
    "zsh": 'eval "$(_ORCA_COMPLETE=zsh_source orca)"',
}
_COMPLETION_MARKER = "_ORCA_COMPLETE="  # presence = already installed

_RC_FILE = {
    "bash": Path("~/.bashrc"),
    "zsh": Path("~/.zshrc"),
}
_FISH_COMPLETION_FILE = Path("~/.config/fish/completions/orca.fish")

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


def detect_shell() -> str | None:
    """Return ``bash``/``zsh``/``fish`` based on ``$SHELL``, or ``None``."""
    shell_env = os.environ.get("SHELL", "")
    if not shell_env:
        return None
    name = Path(shell_env).name
    return name if name in SUPPORTED_SHELLS else None


def install_completion_bashzsh(shell: str) -> str:
    """Append the completion eval line to the shell rc file (idempotent).

    Returns a human-readable status message.
    """
    line = _COMPLETION_EVAL[shell]
    rc = _RC_FILE[shell].expanduser()
    if rc.exists() and _COMPLETION_MARKER in rc.read_text():
        return f"Already present in {rc}."
    rc.parent.mkdir(parents=True, exist_ok=True)
    with rc.open("a") as fh:
        fh.write(f"\n# orca-cli shell completion\n{line}\n")
    return f"Appended to {rc}. Open a new shell or run: source {rc}"


def install_completion_fish() -> str:
    """Generate the fish completion script via ``orca`` and write it to
    ``~/.config/fish/completions/orca.fish``.
    """
    target = _FISH_COMPLETION_FILE.expanduser()
    if target.exists() and _COMPLETION_MARKER in target.read_text():
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
    raise ValueError(f"Unsupported shell: {shell}")
