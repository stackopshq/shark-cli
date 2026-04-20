"""Click helpers for ADR-0008 alias-and-deprecate migrations.

Used when a command is renamed (typically from a legacy hyphenated
form like ``server list-volumes`` to the openstackclient-aligned
``server volume list``). The new name becomes the primary entry; the
old name is registered on the same callback under an
``alias_for=`` short-help marker so users see they should switch.
"""

from __future__ import annotations

import click


class _DeprecatedAliasCommand(click.Command):
    """Wraps a Click command and prints a one-line deprecation hint
    on stderr before invoking the underlying callback.
    """

    def __init__(self, command: click.Command, *, replacement: str) -> None:
        super().__init__(
            name=command.name,
            callback=command.callback,
            params=command.params,
            help=command.help,
            epilog=command.epilog,
            short_help=f"[deprecated, use '{replacement}' instead]",
            options_metavar=command.options_metavar,
            add_help_option=command.add_help_option,
            no_args_is_help=command.no_args_is_help,
            hidden=command.hidden,
            deprecated=True,
            context_settings=command.context_settings,
        )
        self._replacement = replacement

    def invoke(self, ctx: click.Context) -> object:
        click.secho(
            f"warning: '{self.name}' is deprecated; use '{self._replacement}' instead.",
            fg="yellow", err=True,
        )
        return super().invoke(ctx)


def add_command_with_alias(
    group: click.Group,
    primary: click.Command,
    *,
    legacy_name: str,
    primary_path: str,
) -> None:
    """Expose *primary* under *legacy_name* on *group* as a deprecated alias.

    The primary command is **not** re-attached to *group* — the caller
    is expected to have already registered it where it logically
    belongs (typically a sub-group of *group*, e.g.
    ``server.add.port`` while the alias lives directly on ``server``).

    Args:
        group: the Click group that should expose the legacy alias.
        primary: the convention-compliant command object the alias
            forwards to.
        legacy_name: the historical hyphenated name to keep working.
        primary_path: the full new path shown in the deprecation hint
            (e.g. ``"server add port"``).
    """
    if legacy_name == primary.name and group.commands.get(legacy_name) is primary:
        return  # nothing to alias — the command is already at the canonical spot
    alias = _DeprecatedAliasCommand(primary, replacement=primary_path)
    alias.name = legacy_name
    group.add_command(alias, name=legacy_name)
