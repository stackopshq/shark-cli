"""``orca completion`` — generate shell auto-completion scripts."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()

INSTRUCTIONS = {
    "bash": (
        'Add this to your ~/.bashrc:\n'
        '  eval "$(_ORCA_COMPLETE=bash_source orca)"'
    ),
    "zsh": (
        'Add this to your ~/.zshrc:\n'
        '  eval "$(_ORCA_COMPLETE=zsh_source orca)"'
    ),
    "fish": (
        'Run the following command:\n'
        '  _ORCA_COMPLETE=fish_source orca > ~/.config/fish/completions/orca.fish'
    ),
}


@click.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False))
def completion(shell: str) -> None:
    """Generate shell completion script and display installation instructions.

    Supported shells: bash, zsh, fish.
    """
    shell = shell.lower()
    console.print(f"\n[bold cyan]Shell completion for {shell}[/bold cyan]\n")
    console.print(INSTRUCTIONS[shell])
    console.print()
