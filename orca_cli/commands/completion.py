"""``orca completion`` — install shell auto-completion or print instructions."""

from __future__ import annotations

import click
from rich.console import Console

from orca_cli.core.shell_completion import (
    SUPPORTED_SHELLS,
    detect_shell,
    install_completion,
)

console = Console()

INSTRUCTIONS = {
    "bash": (
        'Generate the completion script once and source it at login:\n'
        '  mkdir -p ~/.local/share/orca\n'
        '  _ORCA_COMPLETE=bash_source orca > ~/.local/share/orca/completion.bash\n'
        '\n'
        'Then add this to your ~/.bashrc:\n'
        '  [ -f ~/.local/share/orca/completion.bash ] && source ~/.local/share/orca/completion.bash\n'
        '\n'
        'Why: sourcing a static file at login is microseconds; the previous\n'
        '"eval" pattern re-ran orca on every shell startup (see ADR 0010).'
    ),
    "zsh": (
        'Generate the completion script once and source it at login:\n'
        '  mkdir -p ~/.local/share/orca\n'
        '  _ORCA_COMPLETE=zsh_source orca > ~/.local/share/orca/completion.zsh\n'
        '\n'
        'Then add this to your ~/.zshrc:\n'
        '  [ -f ~/.local/share/orca/completion.zsh ] && source ~/.local/share/orca/completion.zsh\n'
        '\n'
        'Why: sourcing a static file at login is microseconds; the previous\n'
        '"eval" pattern re-ran orca on every shell startup (see ADR 0010).'
    ),
    "fish": (
        'Run the following command:\n'
        '  _ORCA_COMPLETE=fish_source orca > ~/.config/fish/completions/orca.fish'
    ),
}


def _print_instructions(shell: str) -> None:
    console.print(f"\n[bold cyan]Shell completion for {shell}[/bold cyan]\n")
    console.print(INSTRUCTIONS[shell])
    console.print(
        f"\n[dim]Or run 'orca completion install {shell}' "
        f"to install automatically.[/dim]\n"
    )


class _CompletionGroup(click.Group):
    """Group that accepts a bare shell name as shorthand for ``show <shell>``.

    Lets users keep the legacy ``orca completion bash`` UX while also exposing
    the newer ``orca completion install <shell>`` subcommand.
    """

    def resolve_command(self, ctx, args):
        if args and args[0].lower() in SUPPORTED_SHELLS:
            return super().resolve_command(ctx, ["show", *args])
        return super().resolve_command(ctx, args)


@click.group(cls=_CompletionGroup, invoke_without_command=True)
@click.pass_context
def completion(ctx: click.Context) -> None:
    """Shell completion: print instructions or install automatically.

    \b
    Examples:
      orca completion                    # auto-detect shell, print instructions
      orca completion bash               # print instructions for bash (legacy)
      orca completion show zsh           # same, explicit
      orca completion install            # auto-detect shell, install
      orca completion install fish       # install for fish
    """
    if ctx.invoked_subcommand is not None:
        return
    # Bare ``orca completion`` → auto-detect + print
    detected = detect_shell()
    if not detected:
        console.print(
            "[yellow]Could not auto-detect your shell.[/yellow] "
            "Pass one explicitly: [cyan]orca completion <bash|zsh|fish>[/cyan]."
        )
        ctx.exit(1)
    _print_instructions(detected)


@completion.command("show")
@click.argument("shell", required=False,
                type=click.Choice(list(SUPPORTED_SHELLS), case_sensitive=False))
@click.pass_context
def completion_show(ctx: click.Context, shell: str | None) -> None:
    """Print manual installation instructions for the given shell."""
    resolved = shell.lower() if shell else detect_shell()
    if not resolved:
        console.print(
            "[yellow]Could not auto-detect your shell.[/yellow] "
            "Pass one explicitly: [cyan]orca completion show <bash|zsh|fish>[/cyan]."
        )
        ctx.exit(1)
    _print_instructions(resolved)


@completion.command("install")
@click.argument("shell", required=False,
                type=click.Choice(list(SUPPORTED_SHELLS), case_sensitive=False))
@click.pass_context
def completion_install(ctx: click.Context, shell: str | None) -> None:
    """Install orca shell completion (auto-detects shell when omitted).

    \b
    - bash/zsh: appends an eval line to ~/.bashrc / ~/.zshrc (idempotent).
    - fish: writes ~/.config/fish/completions/orca.fish.
    """
    resolved = shell.lower() if shell else detect_shell()
    if not resolved:
        console.print(
            "[red]Could not auto-detect your shell.[/red] "
            "Pass one explicitly: [cyan]orca completion install <bash|zsh|fish>[/cyan]."
        )
        ctx.exit(1)
    msg = install_completion(resolved)
    console.print(f"[green]✓ {msg}[/green]")
