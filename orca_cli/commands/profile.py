"""``orca profile`` — manage configuration profiles (multi-account)."""

from __future__ import annotations

import re
from pathlib import Path

import click

from orca_cli.core.config import (
    _find_clouds_yaml,
    _normalise_legacy_keys,
    delete_profile,
    get_active_profile_name,
    get_profile,
    list_profiles,
    rename_profile,
    save_profile,
    set_active_profile,
)
from orca_cli.core.output import console

_FIELDS = [
    ("auth_url", "Auth URL (Keystone)", "https://keystone.example.com:5000"),
    ("username", "Username", ""),
    ("password", "Password", ""),
    ("user_domain_name", "User Domain Name", "Default"),
    ("project_name", "Project Name", ""),
    ("region_name", "Region Name (leave empty to skip)", ""),
    ("insecure", "Skip SSL verification (true/false)", "true"),
]

_VALID_COLORS = [
    "red", "green", "blue", "yellow", "magenta", "cyan", "white",
    "bright_red", "bright_green", "bright_blue", "bright_yellow",
    "bright_magenta", "bright_cyan", "orange3", "purple", "pink1",
]


def _profile_color(cfg: dict) -> str:
    """Get the color for a profile, or empty string for default."""
    return cfg.get("color", "")


def _active_marker(name: str, cfg: dict, active: str | None) -> str:
    """Return a Rich-marked name with active indicator for the switch wizard."""
    color = _profile_color(cfg)
    marker = "[green bold]●[/green bold] " if name == active else "  "
    if color:
        return f"{marker}[{color}]{name}[/{color}]"
    return f"{marker}{name}"


@click.group()
def profile() -> None:
    """Manage configuration profiles (multi-account)."""
    pass


@profile.command("list")
def profile_list() -> None:
    """List all profiles."""
    from rich.table import Table

    profiles = list_profiles()
    active = get_active_profile_name()

    if not profiles:
        console.print("[yellow]No profiles configured. Run 'orca profile add <name>'.[/yellow]")
        return

    table = Table(title="Profiles", show_lines=False)
    table.add_column("", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Auth URL")
    table.add_column("Username")
    table.add_column("Project")
    table.add_column("Color")

    for name, cfg in sorted(profiles.items()):
        color = _profile_color(cfg)
        marker = "[green bold]●[/green bold]" if name == active else " "
        display_name = f"[{color}]{name}[/{color}]" if color else name
        color_preview = f"[{color}]●[/{color}] {color}" if color else "—"
        project = cfg.get("project_name") or cfg.get("project_id") or "—"
        table.add_row(
            marker,
            display_name,
            cfg.get("auth_url", "—"),
            cfg.get("username", "—"),
            project,
            color_preview,
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]Active: {active}. Switch with 'orca profile switch <name>'.[/dim]\n")


@profile.command("show")
@click.argument("name", required=False, default=None)
def profile_show(name: str | None) -> None:
    """Show profile details. Defaults to active profile."""
    from rich.table import Table

    if not name:
        name = get_active_profile_name()

    cfg = get_profile(name)
    if not cfg:
        raise click.ClickException(f"Profile '{name}' not found.")

    active = get_active_profile_name()
    marker = " (active)" if name == active else ""
    color = _profile_color(cfg)

    title = f"Profile: {name}{marker}"

    table = Table(title=title, show_lines=False)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    _show_keys = [
        "auth_url", "username",
        "user_domain_name", "user_domain_id", "domain_id",
        "project_domain_name", "project_domain_id",
        "project_name", "project_id",
        "region_name", "interface", "insecure", "cacert",
    ]
    for key in _show_keys:
        val = cfg.get(key)
        if val:
            table.add_row(key, str(val))
    table.add_row("password", "●●●●●●●●" if cfg.get("password") else "—")
    color_display = f"[{color}]● {color}[/{color}]" if color else "—"
    table.add_row("color", color_display)

    console.print()
    console.print(table)
    console.print()


@profile.command("add")
@click.argument("name")
@click.option("--copy-from", default=None, help="Copy settings from an existing profile.")
@click.option("--color", "profile_color", default=None, help="Profile color (e.g. red, green, blue, cyan, magenta, yellow).")
def profile_add(name: str, copy_from: str | None, profile_color: str | None) -> None:
    """Add a new profile interactively.

    \b
    Examples:
      orca profile add production
      orca profile add staging --copy-from production --color yellow
    """
    profiles = list_profiles()
    if name in profiles:
        raise click.ClickException(f"Profile '{name}' already exists. Use 'orca profile edit {name}'.")

    console.print(f"\n[bold cyan]New profile: {name}[/bold cyan]\n")

    defaults = get_profile(copy_from) if copy_from else {}
    config_data = {}

    for key, label, placeholder in _FIELDS:
        default = defaults.get(key, placeholder)
        hide = key == "password"
        value = click.prompt(
            f"  {label}",
            default=default if not hide else (default or None),
            hide_input=hide,
            confirmation_prompt=hide,
        )
        config_data[key] = value

    if profile_color:
        config_data["color"] = profile_color

    path = save_profile(name, config_data)
    console.print(f"\n[green]Profile '{name}' saved to {path}.[/green]")

    if len(profiles) == 0:
        set_active_profile(name)
        console.print("[green]Set as active profile.[/green]\n")
    else:
        if click.confirm(f"Switch to '{name}' now?", default=False):
            set_active_profile(name)
            console.print(f"[green]Switched to '{name}'.[/green]\n")


@profile.command("edit")
@click.argument("name", required=False, default=None)
def profile_edit(name: str | None) -> None:
    """Edit an existing profile interactively."""
    if not name:
        name = get_active_profile_name()

    existing = get_profile(name)
    if not existing:
        raise click.ClickException(f"Profile '{name}' not found.")

    console.print(f"\n[bold cyan]Editing profile: {name}[/bold cyan]")
    console.print("[dim]Press Enter to keep current value.[/dim]\n")

    config_data = {}
    for key, label, placeholder in _FIELDS:
        default = existing.get(key, placeholder)
        hide = key == "password"
        value = click.prompt(
            f"  {label}",
            default=default if not hide else (default or None),
            hide_input=hide,
            confirmation_prompt=hide,
        )
        config_data[key] = value

    # Preserve color if set
    if existing.get("color"):
        config_data["color"] = existing["color"]

    save_profile(name, config_data)
    console.print(f"\n[green]Profile '{name}' updated.[/green]\n")


@profile.command("switch")
@click.argument("name", required=False, default=None)
def profile_switch(name: str | None) -> None:
    """Switch the active profile.

    Without a NAME argument, shows an interactive numbered menu.

    \b
    Examples:
      orca profile switch           # interactive menu
      orca profile switch production
      orca profile switch staging
    """
    from orca_cli.core.wizard import wizard_select

    profiles = list_profiles()
    if not profiles:
        raise click.ClickException("No profiles configured. Run 'orca profile add <name>'.")

    if not name:
        active = get_active_profile_name()
        items = sorted(profiles.items())  # list of (name, cfg)

        console.print("\n[bold cyan]Select a profile[/bold cyan]")
        idx = wizard_select(
            items,
            "Profile",
            ["Name", "Project", "Username"],
            lambda item: (
                _active_marker(item[0], item[1], active),
                item[1].get("project_name") or item[1].get("project_id") or "—",
                item[1].get("username", "—"),
            ),
        )
        if idx is None:
            return
        name = items[idx][0]

    try:
        cfg = get_profile(name)
        if not cfg:
            raise KeyError(name)
        set_active_profile(name)
    except KeyError:
        available = ", ".join(sorted(profiles.keys()))
        raise click.ClickException(f"Profile '{name}' not found. Available: {available}")

    color = _profile_color(cfg)
    styled_name = f"[{color} bold]{name}[/{color} bold]" if color else f"[bold]{name}[/bold]"
    console.print(f"[green]Switched to '[/green]{styled_name}[green]'.[/green]")


@profile.command("set-color")
@click.argument("color")
@click.argument("name", required=False, default=None)
def profile_set_color(color: str, name: str | None) -> None:
    """Set a color for a profile. Use 'none' to remove.

    \b
    Available colors:
      red, green, blue, yellow, magenta, cyan, white,
      bright_red, bright_green, bright_blue, bright_yellow,
      bright_magenta, bright_cyan, orange3, purple, pink1

    \b
    Examples:
      orca profile set-color red
      orca profile set-color blue production
      orca profile set-color none staging
    """
    if not name:
        name = get_active_profile_name()

    cfg = get_profile(name)
    if not cfg:
        raise click.ClickException(f"Profile '{name}' not found.")

    if color.lower() == "none":
        cfg.pop("color", None)
        save_profile(name, cfg)
        console.print(f"[green]Color removed from profile '{name}'.[/green]")
    else:
        cfg["color"] = color
        save_profile(name, cfg)
        console.print(f"Color set for profile '[{color} bold]{name}[/{color} bold]'.")


@profile.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def profile_remove(name: str, yes: bool) -> None:
    """Remove a profile."""
    if not yes:
        click.confirm(f"Delete profile '{name}'?", abort=True)
    try:
        delete_profile(name)
    except KeyError:
        raise click.ClickException(f"Profile '{name}' not found.")
    except ValueError as e:
        raise click.ClickException(str(e))
    console.print(f"[green]Profile '{name}' removed.[/green]")


def _complete_regions(ctx: click.Context, param: click.Parameter, incomplete: str) -> list:
    """Shell completion for region names — authenticates and reads the catalog."""
    try:
        from orca_cli.core.client import OrcaClient
        from orca_cli.core.config import config_is_complete, load_config

        config = load_config()
        if not config_is_complete(config):
            return []
        client = OrcaClient(config)
        regions: set[str] = set()
        for svc in client._catalog:
            for ep in svc.get("endpoints", []):
                region = ep.get("region_id") or ep.get("region")
                if region:
                    regions.add(region)
        client.close()
        completions = sorted(r for r in regions if r.startswith(incomplete))
        if "none".startswith(incomplete):
            completions.append("none")
        return completions
    except Exception:
        return []


@profile.command("set-region")
@click.argument("region", shell_complete=_complete_regions)
@click.argument("name", required=False, default=None)
def profile_set_region(region: str, name: str | None) -> None:
    """Set the default region for a profile.

    Use 'none' to clear the region (use the first available).

    \b
    Examples:
      orca profile set-region dc3-a
      orca profile set-region dc4-a production
      orca profile set-region none               # clear region
    """
    if not name:
        name = get_active_profile_name()

    cfg = get_profile(name)
    if not cfg:
        raise click.ClickException(f"Profile '{name}' not found.")

    if region.lower() == "none":
        cfg.pop("region_name", None)
        save_profile(name, cfg)
        console.print(f"[green]Region cleared for profile '{name}'.[/green]")
    else:
        cfg["region_name"] = region
        save_profile(name, cfg)
        console.print(f"[green]Region set to '[bold]{region}[/bold]' for profile '{name}'.[/green]")


@profile.command("regions")
@click.pass_context
def profile_regions(ctx: click.Context) -> None:
    """List available regions from the Keystone service catalog.

    Authenticates with the current profile and inspects the catalog
    to show which regions are available.

    \b
    Examples:
      orca profile regions
      orca -P infomaniak profile regions
    """
    from orca_cli.core.context import OrcaContext

    client = ctx.find_object(OrcaContext).ensure_client()

    regions: set[str] = set()
    for svc in client._catalog:
        for ep in svc.get("endpoints", []):
            region = ep.get("region_id") or ep.get("region")
            if region:
                regions.add(region)

    if not regions:
        console.print("[yellow]No regions found in the service catalog.[/yellow]")
        return

    current = client._region_name
    from rich.table import Table

    table = Table(title="Available Regions", show_lines=False)
    table.add_column("", no_wrap=True)
    table.add_column("Region", style="bold")

    for r in sorted(regions):
        marker = "[green bold]●[/green bold]" if r == current else " "
        table.add_row(marker, r)

    console.print()
    console.print(table)
    if current:
        console.print(f"\n[dim]Current region: {current}. Switch with 'orca profile set-region <region>'.[/dim]")
    else:
        console.print("\n[dim]No region set. Set with 'orca profile set-region <region>' or 'orca -R <region> <command>'.[/dim]")
    console.print()


@profile.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def profile_rename(old_name: str, new_name: str) -> None:
    """Rename a profile."""
    try:
        rename_profile(old_name, new_name)
    except (KeyError, ValueError) as e:
        raise click.ClickException(str(e))
    console.print(f"[green]Profile '{old_name}' renamed to '{new_name}'.[/green]")


# ── Export / Import ─────────────────────────────────────────────────────

def _resolve_config(name: str | None) -> tuple[str, dict]:
    """Return (profile_name, resolved_config) for export commands."""
    if not name:
        name = get_active_profile_name()
    cfg = get_profile(name)
    if not cfg:
        raise click.ClickException(f"Profile '{name}' not found.")
    _normalise_legacy_keys(cfg)
    return name, cfg


def _cfg_to_os_env(cfg: dict) -> dict[str, str]:
    """Map a resolved config dict to OS_* env var names."""
    m: dict[str, str] = {}
    if cfg.get("auth_url"):
        m["OS_AUTH_URL"] = cfg["auth_url"]
    if cfg.get("username"):
        m["OS_USERNAME"] = cfg["username"]
    if cfg.get("password"):
        m["OS_PASSWORD"] = cfg["password"]
    if cfg.get("user_domain_name"):
        m["OS_USER_DOMAIN_NAME"] = cfg["user_domain_name"]
    elif cfg.get("user_domain_id"):
        m["OS_USER_DOMAIN_ID"] = cfg["user_domain_id"]
    if cfg.get("project_domain_name"):
        m["OS_PROJECT_DOMAIN_NAME"] = cfg["project_domain_name"]
    elif cfg.get("project_domain_id"):
        m["OS_PROJECT_DOMAIN_ID"] = cfg["project_domain_id"]
    if cfg.get("project_name"):
        m["OS_PROJECT_NAME"] = cfg["project_name"]
    elif cfg.get("project_id"):
        m["OS_PROJECT_ID"] = cfg["project_id"]
    if cfg.get("region_name"):
        m["OS_REGION_NAME"] = cfg["region_name"]
    if cfg.get("interface"):
        m["OS_INTERFACE"] = cfg["interface"]
    if cfg.get("cacert"):
        m["OS_CACERT"] = cfg["cacert"]
    m["OS_IDENTITY_API_VERSION"] = "3"
    return m


@profile.command("to-openrc")
@click.argument("name", required=False, default=None)
@click.option("--output", "-o", "output_file", default=None,
              help="Write to file instead of stdout.")
def profile_to_openrc(name: str | None, output_file: str | None) -> None:
    """Export a profile as an OpenRC shell script.

    \b
    Examples:
      orca profile to-openrc                     # active profile to stdout
      orca profile to-openrc production           # specific profile
      orca profile to-openrc production -o prod-openrc.sh
      source <(orca profile to-openrc)            # source directly
    """
    name, cfg = _resolve_config(name)
    env_vars = _cfg_to_os_env(cfg)

    lines = [f"# OpenRC for orca profile '{name}'"]
    for key, val in env_vars.items():
        lines.append(f"export {key}={_shell_quote(val)}")

    output = "\n".join(lines) + "\n"

    if output_file:
        Path(output_file).write_text(output)
        console.print(f"[green]OpenRC written to {output_file}[/green]")
    else:
        click.echo(output, nl=False)


@profile.command("to-clouds")
@click.argument("name", required=False, default=None)
@click.option("--output", "-o", "output_file", default=None,
              help="Write to file instead of stdout.")
@click.option("--cloud-name", default=None,
              help="Cloud name in clouds.yaml (default: profile name).")
def profile_to_clouds(name: str | None, output_file: str | None, cloud_name: str | None) -> None:
    """Export a profile as a clouds.yaml entry.

    \b
    Examples:
      orca profile to-clouds                          # active profile
      orca profile to-clouds production               # specific profile
      orca profile to-clouds production -o clouds.yaml
    """
    import yaml

    name, cfg = _resolve_config(name)
    cname = cloud_name or name

    auth: dict[str, str] = {}
    if cfg.get("auth_url"):
        auth["auth_url"] = cfg["auth_url"]
    if cfg.get("username"):
        auth["username"] = cfg["username"]
    if cfg.get("password"):
        auth["password"] = cfg["password"]
    if cfg.get("user_domain_name"):
        auth["user_domain_name"] = cfg["user_domain_name"]
    elif cfg.get("user_domain_id"):
        auth["user_domain_id"] = cfg["user_domain_id"]
    if cfg.get("project_domain_name"):
        auth["project_domain_name"] = cfg["project_domain_name"]
    elif cfg.get("project_domain_id"):
        auth["project_domain_id"] = cfg["project_domain_id"]
    if cfg.get("project_name"):
        auth["project_name"] = cfg["project_name"]
    elif cfg.get("project_id"):
        auth["project_id"] = cfg["project_id"]

    cloud: dict[str, any] = {"auth": auth}
    if cfg.get("region_name"):
        cloud["region_name"] = cfg["region_name"]
    if cfg.get("interface"):
        cloud["interface"] = cfg["interface"]
    if cfg.get("cacert"):
        cloud["cacert"] = cfg["cacert"]
    if str(cfg.get("insecure", "false")).lower() in ("true", "1", "yes"):
        cloud["verify"] = False

    data = {"clouds": {cname: cloud}}
    output = yaml.dump(data, default_flow_style=False, sort_keys=False)

    if output_file:
        Path(output_file).write_text(output)
        console.print(f"[green]clouds.yaml written to {output_file}[/green]")
    else:
        click.echo(output, nl=False)


@profile.command("from-openrc")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", "-n", "profile_name", default=None,
              help="Profile name (default: filename without extension).")
def profile_from_openrc(file: str, profile_name: str | None) -> None:
    """Import an OpenRC file as an orca profile.

    \b
    Examples:
      orca profile from-openrc admin-openrc.sh
      orca profile from-openrc admin-openrc.sh --name production
    """
    path = Path(file)
    name = profile_name or path.stem.replace("-openrc", "").replace("_openrc", "")
    if not name:
        name = "imported"

    env_vars = _parse_openrc(path.read_text())
    if not env_vars.get("OS_AUTH_URL"):
        raise click.ClickException(f"No OS_AUTH_URL found in {file}.")

    cfg = _os_env_to_cfg(env_vars)

    profiles = list_profiles()
    if name in profiles:
        if not click.confirm(f"Profile '{name}' exists. Overwrite?"):
            raise SystemExit(0)

    save_profile(name, cfg)
    console.print(f"[green]Profile '{name}' imported from {file}.[/green]")


@profile.command("from-clouds")
@click.argument("cloud_name")
@click.option("--name", "-n", "profile_name", default=None,
              help="Profile name (default: cloud name).")
@click.option("--file", "-f", "clouds_file", default=None,
              help="Path to clouds.yaml (default: auto-detect).")
def profile_from_clouds(cloud_name: str, profile_name: str | None, clouds_file: str | None) -> None:
    """Import a cloud from clouds.yaml as an orca profile.

    \b
    Examples:
      orca profile from-clouds mycloud
      orca profile from-clouds mycloud --name production
      orca profile from-clouds mycloud -f /path/to/clouds.yaml
    """
    import yaml

    if clouds_file:
        p = Path(clouds_file)
        if not p.exists():
            raise click.ClickException(f"File not found: {clouds_file}")
        with open(p, "r") as fh:
            data = yaml.safe_load(fh) or {}
        cloud = data.get("clouds", {}).get(cloud_name)
    else:
        found = _find_clouds_yaml()
        if not found:
            raise click.ClickException(
                "No clouds.yaml found. Searched: ./clouds.yaml, "
                "~/.config/openstack/clouds.yaml, /etc/openstack/clouds.yaml"
            )
        with open(found, "r") as fh:
            data = yaml.safe_load(fh) or {}
        cloud = data.get("clouds", {}).get(cloud_name)
        if not cloud:
            available = ", ".join(sorted(data.get("clouds", {}).keys()))
            raise click.ClickException(
                f"Cloud '{cloud_name}' not found. Available: {available or 'none'}"
            )

    if not cloud:
        raise click.ClickException(f"Cloud '{cloud_name}' not found in file.")

    from orca_cli.core.config import _normalise_clouds_yaml
    cfg = _normalise_clouds_yaml(cloud)

    name = profile_name or cloud_name
    profiles = list_profiles()
    if name in profiles:
        if not click.confirm(f"Profile '{name}' exists. Overwrite?"):
            raise SystemExit(0)

    save_profile(name, cfg)
    console.print(f"[green]Profile '{name}' imported from clouds.yaml (cloud: {cloud_name}).[/green]")


# ── Helpers ─────────────────────────────────────────────────────────────

def _shell_quote(val: str) -> str:
    """Quote a value for safe shell use."""
    if re.match(r'^[A-Za-z0-9_./:@-]+$', val):
        return val
    return "'" + val.replace("'", "'\\''") + "'"


def _parse_openrc(content: str) -> dict[str, str]:
    """Parse export lines from an OpenRC script."""
    env: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Match: export KEY=VALUE or export KEY="VALUE" or export KEY='VALUE'
        m = re.match(r'^export\s+([A-Z_]+)=(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            env[key] = val
    return env


def _os_env_to_cfg(env: dict[str, str]) -> dict[str, str]:
    """Convert OS_* env dict to orca config dict."""
    cfg: dict[str, str] = {}
    if env.get("OS_AUTH_URL"):
        cfg["auth_url"] = env["OS_AUTH_URL"]
    if env.get("OS_USERNAME"):
        cfg["username"] = env["OS_USERNAME"]
    if env.get("OS_PASSWORD"):
        cfg["password"] = env["OS_PASSWORD"]
    if env.get("OS_USER_DOMAIN_NAME"):
        cfg["user_domain_name"] = env["OS_USER_DOMAIN_NAME"]
    elif env.get("OS_USER_DOMAIN_ID"):
        cfg["user_domain_id"] = env["OS_USER_DOMAIN_ID"]
    if env.get("OS_PROJECT_DOMAIN_NAME"):
        cfg["project_domain_name"] = env["OS_PROJECT_DOMAIN_NAME"]
    elif env.get("OS_PROJECT_DOMAIN_ID"):
        cfg["project_domain_id"] = env["OS_PROJECT_DOMAIN_ID"]
    if env.get("OS_PROJECT_NAME"):
        cfg["project_name"] = env["OS_PROJECT_NAME"]
    elif env.get("OS_PROJECT_ID"):
        cfg["project_id"] = env["OS_PROJECT_ID"]
    if env.get("OS_REGION_NAME"):
        cfg["region_name"] = env["OS_REGION_NAME"]
    if env.get("OS_INTERFACE"):
        cfg["interface"] = env["OS_INTERFACE"]
    if env.get("OS_CACERT"):
        cfg["cacert"] = env["OS_CACERT"]
    if env.get("OS_INSECURE"):
        cfg["insecure"] = env["OS_INSECURE"]
    return cfg
