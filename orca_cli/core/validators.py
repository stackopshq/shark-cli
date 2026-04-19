"""Input validators for CLI options and arguments."""

import re

import click


def validate_id(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate that the given value looks like a valid resource ID.

    Accepts:
    - Hyphenated UUID: ``8-4-4-4-12`` hex (e.g. Nova/Neutron resource IDs).
    - Bare hex UUID: 32 hex chars (e.g. Keystone project/user IDs).
    - Numeric ID (e.g. flavor IDs on older clouds, quota resources).
    """
    # Pass through None so the callback is safe on optional parameters
    # (Click calls callbacks even when the option was not supplied).
    if value is None:
        return value
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    hex_pattern = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
    numeric_pattern = re.compile(r"^\d+$")
    if not (uuid_pattern.match(value) or hex_pattern.match(value) or numeric_pattern.match(value)):
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
