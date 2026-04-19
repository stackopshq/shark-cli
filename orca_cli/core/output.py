"""Shared output formatting for orca commands."""

from __future__ import annotations

import json as _json
from typing import Any, Callable

import click
from rich.console import Console
from rich.table import Table

console = Console()


def output_options(f: Any) -> Any:
    """Add ``--format``, ``--column``, ``--fit-width``, ``--max-width`` and ``--noindent`` options."""
    f = click.option(
        "--format", "-f", "output_format",
        type=click.Choice(["table", "json", "value"], case_sensitive=False),
        default="table", show_default=True,
        help="Output format.",
    )(f)
    f = click.option(
        "--column", "-c", "columns",
        multiple=True,
        help="Column to include (repeatable). Shows all if omitted.",
    )(f)
    f = click.option(
        "--fit-width", "fit_width",
        is_flag=True, default=False,
        help="Fit table to terminal width.",
    )(f)
    f = click.option(
        "--max-width", "max_width",
        type=int, default=None,
        help="Maximum table width (0 = unlimited).",
    )(f)
    f = click.option(
        "--noindent", "noindent",
        is_flag=True, default=False,
        help="Disable JSON indentation.",
    )(f)
    return f


def _table_kwargs(fit_width: bool = False, max_width: int | None = None) -> dict:
    kw: dict = {}
    if max_width is not None:
        kw["width"] = max_width if max_width > 0 else None
    if fit_width:
        kw["width"] = console.width
    return kw


def _json_indent(noindent: bool) -> int | None:
    return None if noindent else 2


def print_list(
    items: list[dict],
    column_defs: list[tuple],
    *,
    title: str = "",
    output_format: str = "table",
    columns: tuple[str, ...] = (),
    empty_msg: str = "No results found.",
    fit_width: bool = False,
    max_width: int | None = None,
    noindent: bool = False,
) -> None:
    """Render a list of resources.

    *column_defs*: list of tuples — each is one of:
        ``("Header", "dict_key")``
        ``("Header", callable)``
        ``("Header", "dict_key", {style_kwargs})``
        ``("Header", callable, {style_kwargs})``
    """
    if not items:
        if output_format == "json":
            click.echo("[]")
        else:
            console.print(f"[yellow]{empty_msg}[/yellow]")
        return

    # Filter columns
    if columns:
        col_set = {c.lower() for c in columns}
        column_defs = [cd for cd in column_defs if cd[0].lower() in col_set]

    if output_format == "json":
        result = []
        for item in items:
            row = {}
            for cd in column_defs:
                header, key = cd[0], cd[1]
                row[header] = _extract(item, key)
            result.append(row)
        click.echo(_json.dumps(result, default=str, indent=_json_indent(noindent)))
        return

    if output_format == "value":
        for item in items:
            vals = [str(_extract(item, cd[1])) for cd in column_defs]
            click.echo(" ".join(vals))
        return

    # table
    width_kw = _table_kwargs(fit_width, max_width)
    table = Table(title=title or None, show_lines=False)
    for cd in column_defs:
        header = cd[0]
        style_kw = cd[2] if len(cd) > 2 else {}
        col_kw = dict(style_kw)
        if fit_width or max_width is not None:
            col_kw.setdefault("overflow", "fold")
        table.add_column(header, **col_kw)

    for item in items:
        row = [str(_extract(item, cd[1])) for cd in column_defs]
        table.add_row(*row)

    console.print(table, **width_kw)


def print_detail(
    fields: list[tuple[str, Any]],
    *,
    output_format: str = "table",
    columns: tuple[str, ...] = (),
    fit_width: bool = False,
    max_width: int | None = None,
    noindent: bool = False,
) -> None:
    """Render a single resource detail view (Field / Value)."""
    if columns:
        col_set = {c.lower() for c in columns}
        fields = [(f, v) for f, v in fields if f.lower() in col_set]

    if output_format == "json":
        data = {f: v for f, v in fields}
        click.echo(_json.dumps(data, default=str, indent=_json_indent(noindent)))
        return

    if output_format == "value":
        for _, value in fields:
            click.echo(value if value is not None else "")
        return

    # table
    width_kw = _table_kwargs(fit_width, max_width)
    table = Table(show_header=True, show_lines=False)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    col_kw: dict = {}
    if fit_width or max_width is not None:
        col_kw["overflow"] = "fold"
    table.add_column("Value", **col_kw)
    for field, value in fields:
        table.add_row(field, str(value) if value is not None else "")
    console.print(table, **width_kw)


def _extract(item: dict, key: str | Callable) -> Any:
    if callable(key):
        return key(item)
    return item.get(key, "")
