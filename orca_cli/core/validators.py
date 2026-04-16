"""Input validators for CLI options and arguments."""

import re

import click


def validate_id(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate that the given value looks like a valid resource ID (UUID or numeric)."""
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    numeric_pattern = re.compile(r"^\d+$")
    if not (uuid_pattern.match(value) or numeric_pattern.match(value)):
        raise click.BadParameter(f"'{value}' is not a valid resource ID (expected UUID or numeric).")
    return value


def validate_ip(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate an IPv4 address."""
    parts = value.split(".")
    if len(parts) != 4:
        raise click.BadParameter(f"'{value}' is not a valid IPv4 address.")
    for part in parts:
        try:
            num = int(part)
        except ValueError:
            raise click.BadParameter(f"'{value}' is not a valid IPv4 address.")
        if not 0 <= num <= 255:
            raise click.BadParameter(f"'{value}' is not a valid IPv4 address.")
    return value
