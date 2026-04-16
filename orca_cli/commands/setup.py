"""``orca setup`` — interactive assistant to configure OpenStack credentials."""

from __future__ import annotations

import click
from rich.console import Console

from orca_cli.core.config import (
    get_active_profile_name,
    list_profiles,
    load_config,
    save_profile,
    set_active_profile,
)
from orca_cli.core.context import OrcaContext

console = Console()

_FIELDS = [
    ("auth_url", "Auth URL (Keystone)", "https://keystone.example.com:5000"),
    ("username", "Username", ""),
    ("password", "Password", ""),
    ("user_domain_name", "User Domain Name", "Default"),
    ("project_name", "Project Name", ""),
    ("region_name", "Region Name (leave empty to skip)", ""),
    ("insecure", "Skip SSL verification (true/false)", "true"),
]


@click.command()
@click.option("--profile", "-p", "profile_name", default=None,
              help="Profile name to create/edit. Default: active profile.")
@click.pass_context
def setup(ctx: click.Context, profile_name: str | None) -> None:
    """Interactive assistant to configure your OpenStack credentials.

    Creates or edits a profile. Use --profile to target a specific profile.

    \b
    Examples:
      orca setup                    # edit the active profile
      orca setup --profile staging  # create/edit 'staging' profile
    """
    # Resolve profile name
    orca_ctx = ctx.find_object(OrcaContext)
    name = profile_name or (orca_ctx.profile if orca_ctx else None) or get_active_profile_name()

    profiles = list_profiles()
    is_new = name not in profiles

    if is_new:
        console.print(f"\n[bold cyan]orca Setup — new profile: {name}[/bold cyan]")
    else:
        console.print(f"\n[bold cyan]orca Setup — editing profile: {name}[/bold cyan]")
    console.print(
        "[dim]Values are available in your OpenStack dashboard or cloud provider portal.[/dim]\n"
    )

    existing = load_config(profile_name=name) if not is_new else {}
    config_data = {}

    for key, label, placeholder in _FIELDS:
        default = existing.get(key, placeholder)
        # Legacy key fallbacks for editing old profiles
        if not default and key == "user_domain_name":
            default = existing.get("domain_id", placeholder)
        if not default and key == "project_name":
            default = existing.get("project_id", placeholder)
        hide = key == "password"
        value = click.prompt(
            f"  {label}",
            default=default if not hide else (default or None),
            hide_input=hide,
            confirmation_prompt=hide,
        )
        if value:  # skip empty optional fields like region_name
            config_data[key] = value

    path = save_profile(name, config_data)
    console.print(f"\n[green]Profile '{name}' saved to {path} (permissions 600).[/green]")

    # If it's a new profile and no profiles existed before, activate it
    if is_new:
        if not profiles:
            set_active_profile(name)
            console.print("[green]Set as active profile.[/green]\n")
        elif click.confirm(f"Switch to '{name}' now?", default=True):
            set_active_profile(name)
            console.print(f"[green]Switched to '{name}'.[/green]\n")
    else:
        console.print()
