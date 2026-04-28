"""Input validators for CLI options and arguments."""

import re
from pathlib import Path
from typing import Union

import click


def validate_id(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate that the given value looks like a valid resource ID.

    Accepts:
    - Hyphenated UUID: ``8-4-4-4-12`` hex (e.g. Nova/Neutron resource IDs).
    - Bare hex UUID: 32 hex chars (e.g. Keystone project/user IDs).
    - SHA-256 hex: 64 hex chars (e.g. Keystone credential IDs).
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
    hex32_pattern = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
    hex64_pattern = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
    numeric_pattern = re.compile(r"^\d+$")
    if not (uuid_pattern.match(value) or hex32_pattern.match(value)
            or hex64_pattern.match(value) or numeric_pattern.match(value)):
        raise click.BadParameter(f"'{value}' is not a valid resource ID (expected UUID or numeric).")
    return value


def safe_output_path(user_path: Union[str, Path]) -> Path:
    """Resolve a user-supplied output path, refusing symlink overwrites.

    Accepts any path (absolute or relative); users are root of their own
    machine and a CLI must not second-guess where they want to save a file.
    What it **does** reject is overwriting an *existing symlink*: an
    attacker who can pre-create ``~/orca-export.yaml -> /etc/shadow`` in
    a shared temp dir would otherwise get the CLI to clobber the link
    target. Delete the link and re-run if this is intentional.
    """
    p = Path(user_path).expanduser()
    if p.is_symlink():
        raise click.BadParameter(
            f"Refusing to write to {p}: path exists as a symlink. "
            "Remove or rename it before re-running (symlink-race guard)."
        )
    return p


def safe_child_path(base: Union[str, Path], child: str) -> Path:
    """Join an API-derived name onto a base directory without escaping it.

    Used for bulk downloads where the child name (object key, file name,
    attachment path) comes from a remote response and could contain ``..``
    segments or an absolute prefix. The resolved path must live under the
    resolved ``base``; anything else raises ``click.BadParameter``.
    """
    base_path = Path(base).expanduser().resolve()
    candidate = (base_path / child).resolve()
    try:
        candidate.relative_to(base_path)
    except ValueError as exc:
        raise click.BadParameter(
            f"Refusing to write {candidate}: resolves outside {base_path} "
            f"(suspicious path segment in {child!r})."
        ) from exc
    return candidate


def validate_ip(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate an IPv4 address."""
    parts = value.split(".")
    if len(parts) != 4:
        raise click.BadParameter(f"'{value}' is not a valid IPv4 address.")
    for part in parts:
        try:
            num = int(part)
        except ValueError as exc:
            raise click.BadParameter(f"'{value}' is not a valid IPv4 address.") from exc
        if not 0 <= num <= 255:
            raise click.BadParameter(f"'{value}' is not a valid IPv4 address.")
    return value
