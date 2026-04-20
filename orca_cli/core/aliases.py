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
    """Register *primary* on *group* under its current name AND under
    *legacy_name* (as a deprecated alias).

    Args:
        group: the Click group both commands attach to.
        primary: the new (convention-compliant) command object.
        legacy_name: the old hyphenated name to keep as an alias.
        primary_path: the new full path shown in the deprecation hint
            (e.g. ``"server volume list"``).
    """
    group.add_command(primary)
    if legacy_name == primary.name:
        return
    alias = _DeprecatedAliasCommand(primary, replacement=primary_path)
    alias.name = legacy_name
    group.add_command(alias, name=legacy_name)
