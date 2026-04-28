"""Tests for the ADR-0008 alias helpers in ``orca_cli.core.aliases``."""

from __future__ import annotations

import click

from orca_cli.core.aliases import (
    add_command_with_alias,
    count_deprecated_aliases,
    list_deprecated_aliases,
)


def _build_tree() -> click.Group:
    """Build a minimal nested CLI with two aliases for the suite."""

    @click.group()
    def root() -> None:
        pass

    @root.group("color")
    def color() -> None:
        pass

    @color.command("set")
    def color_set() -> None:
        pass

    @root.command("show")
    def show() -> None:
        pass

    add_command_with_alias(root, color_set,
                           legacy_name="set-color",
                           primary_path="color set")
    add_command_with_alias(root, show,
                           legacy_name="display",
                           primary_path="show")
    return root


def test_count_deprecated_aliases_walks_subgroups():
    root = _build_tree()
    assert count_deprecated_aliases(root) == 2


def test_count_deprecated_aliases_returns_zero_on_clean_tree():
    @click.group()
    def empty() -> None:
        pass

    @empty.command("a")
    def a() -> None:
        pass

    assert count_deprecated_aliases(empty) == 0


def test_list_deprecated_aliases_returns_full_paths_and_replacements():
    root = _build_tree()
    rows = sorted(list_deprecated_aliases(root))
    assert rows == [
        ("display", "show"),
        ("set-color", "color set"),
    ]


def test_count_deprecated_aliases_on_live_orca_tree_is_positive():
    """Sanity check: the live orca tree carries ADR-0008 aliases today.

    This will read 0 once 3.0.0 ships and the aliases are dropped — at
    that point the assertion can flip to ``== 0`` and this test becomes
    the ratchet that prevents reintroducing aliases without intent.
    """
    from orca_cli.main import cli

    assert count_deprecated_aliases(cli) > 0
