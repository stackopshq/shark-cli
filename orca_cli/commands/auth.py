"""``orca auth`` — Keystone identity & access diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone

import click

from orca_cli.core.config import (
    load_config,
    config_is_complete,
    get_active_profile_name,
    list_profiles,
    _find_clouds_yaml,
    _load_clouds_yaml,
)
from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail


@click.group()
def auth() -> None:
    """Keystone identity & access diagnostics."""
    pass


# ── whoami ──────────────────────────────────────────────────────────────

@auth.command("whoami")
@click.pass_context
def auth_whoami(ctx: click.Context) -> None:
    """Show current identity — user, project, roles, endpoints.

    Fast summary of who you are and what you can do, without listing
    all resources.

    \b
    Examples:
      orca auth whoami
      orca -P staging auth whoami
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    td = client._token_data

    user = td.get("user", {})
    project = td.get("project", {})
    roles = td.get("roles", [])
    expires = td.get("expires_at", "")
    issued = td.get("issued_at", "")

    # Parse expiration
    remaining = ""
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = exp_dt - now
            total_s = int(delta.total_seconds())
            if total_s > 0:
                hours, rem = divmod(total_s, 3600)
                mins, secs = divmod(rem, 60)
                remaining = f"{hours}h {mins}m {secs}s"
            else:
                remaining = "[red bold]EXPIRED[/red bold]"
        except (ValueError, TypeError):
            remaining = "?"

    role_names = ", ".join(sorted(r.get("name", r.get("id", "?")) for r in roles))

    # Services available
    service_types = sorted(set(s.get("type", "?") for s in client._catalog))

    console.print()
    from rich.table import Table

    table = Table(title="orca whoami", show_lines=False, title_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("User", f"{user.get('name', '?')}  [dim]({user.get('id', '?')})[/dim]")
    table.add_row("Domain", f"{user.get('domain', {}).get('name', '?')}  [dim]({user.get('domain', {}).get('id', '?')})[/dim]")
    table.add_row("Project", f"{project.get('name', '?')}  [dim]({project.get('id', '?')})[/dim]")
    table.add_row("Project Domain", f"{project.get('domain', {}).get('name', '?')}  [dim]({project.get('domain', {}).get('id', '?')})[/dim]")
    table.add_row("Roles", role_names or "[dim]none[/dim]")
    table.add_row("Token Issued", issued.replace("T", " ").replace("Z", " UTC") if issued else "?")
    table.add_row("Token Expires", f"{expires.replace('T', ' ').replace('Z', ' UTC')}  [bold]({remaining})[/bold]" if expires else "?")
    table.add_row("Auth URL", client._auth_url)
    table.add_row("Interface", client._interface)
    if client._region_name:
        table.add_row("Region", client._region_name)
    table.add_row("Services", ", ".join(service_types) if service_types else "[dim]none[/dim]")

    console.print(table)
    console.print()


# ── token-debug ─────────────────────────────────────────────────────────

@auth.command("token-debug")
@click.option("--raw", is_flag=True, default=False,
              help="Print the full token body as JSON.")
@click.pass_context
def auth_token_debug(ctx: click.Context, raw: bool) -> None:
    """Inspect the current token — roles, catalog, methods, expiration.

    Shows everything Keystone returned in the token payload.
    Use --raw for the full JSON dump.

    \b
    Examples:
      orca auth token-debug
      orca auth token-debug --raw
    """
    import json

    client = ctx.find_object(OrcaContext).ensure_client()
    td = client._token_data

    if raw:
        click.echo(json.dumps(td, indent=2, default=str))
        return

    from rich.table import Table
    from rich.tree import Tree
    from rich.text import Text

    user = td.get("user", {})
    project = td.get("project", {})
    roles = td.get("roles", [])
    methods = td.get("methods", [])
    expires = td.get("expires_at", "")
    issued = td.get("issued_at", "")

    console.print()

    # ── Token summary ──
    table = Table(title="Token Debug", show_lines=False, title_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Token (first 32)", (client._token or "")[:32] + "…")
    table.add_row("Auth Methods", ", ".join(methods))
    table.add_row("Issued At", issued)
    table.add_row("Expires At", expires)

    # Time analysis
    if issued and expires:
        try:
            iss = datetime.fromisoformat(issued.replace("Z", "+00:00"))
            exp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            lifetime = exp - iss
            remaining = exp - now
            elapsed = now - iss
            pct = (elapsed.total_seconds() / lifetime.total_seconds() * 100) if lifetime.total_seconds() > 0 else 0
            color = "green" if pct < 50 else "yellow" if pct < 80 else "red"
            table.add_row("Lifetime", str(lifetime))
            table.add_row("Remaining", f"[{color}]{remaining}[/{color}]  ({pct:.0f}% elapsed)")
        except (ValueError, TypeError):
            pass

    table.add_row("User", f"{user.get('name')} ({user.get('id', '?')})")
    table.add_row("User Domain", f"{user.get('domain', {}).get('name')} ({user.get('domain', {}).get('id', '?')})")
    table.add_row("Project", f"{project.get('name')} ({project.get('id', '?')})")
    table.add_row("Project Domain", f"{project.get('domain', {}).get('name')} ({project.get('domain', {}).get('id', '?')})")

    console.print(table)

    # ── Roles ──
    console.print()
    role_table = Table(title="Roles", show_lines=False)
    role_table.add_column("Name", style="bold green")
    role_table.add_column("ID", style="dim")
    for r in sorted(roles, key=lambda x: x.get("name", "")):
        role_table.add_row(r.get("name", "?"), r.get("id", "?"))
    console.print(role_table)

    # ── Service Catalog ──
    console.print()
    tree = Tree("[bold]Service Catalog[/bold]")
    for svc in sorted(client._catalog, key=lambda s: s.get("type", "")):
        stype = svc.get("type", "?")
        sname = svc.get("name", "")
        branch = tree.add(f"[bold cyan]{stype}[/bold cyan]  [dim]({sname})[/dim]")
        for ep in svc.get("endpoints", []):
            iface = ep.get("interface", "?")
            url = ep.get("url", "?")
            region = ep.get("region_id", "")
            style = "green" if iface == "public" else "yellow" if iface == "internal" else "red"
            region_str = f"  [dim]{region}[/dim]" if region else ""
            branch.add(f"[{style}]{iface}[/{style}]: {url}{region_str}")

    console.print(tree)
    console.print()


# ── check (pwc) ─────────────────────────────────────────────────────────

@auth.command("check")
@click.option("--all", "-a", "check_all", is_flag=True, default=False,
              help="Check all profiles, not just the active one.")
@click.option("--clouds", is_flag=True, default=False,
              help="Also check clouds.yaml entries.")
@click.pass_context
def auth_check(ctx: click.Context, check_all: bool, clouds: bool) -> None:
    """Verify credentials are still valid (password check).

    Tests authentication against Keystone without running any command.
    Use before long scripts to fail fast.

    \b
    Examples:
      orca auth check              # check active profile
      orca auth check --all        # check every orca profile
      orca auth check --clouds     # also check clouds.yaml entries
    """
    from orca_cli.core.client import OrcaClient

    targets: list[tuple[str, dict]] = []

    if check_all:
        for name, cfg in sorted(list_profiles().items()):
            targets.append((f"profile:{name}", cfg))
    else:
        orca_ctx = ctx.find_object(OrcaContext)
        profile_name = orca_ctx.profile if orca_ctx else None
        name = get_active_profile_name(profile_name)
        cfg = load_config(profile_name=profile_name)
        targets.append((f"profile:{name}", cfg))

    if clouds:
        import yaml
        path = _find_clouds_yaml()
        if path:
            with open(path, "r") as fh:
                data = yaml.safe_load(fh) or {}
            for cloud_name in sorted(data.get("clouds", {}).keys()):
                cfg = _load_clouds_yaml(cloud_name)
                if cfg:
                    targets.append((f"cloud:{cloud_name}", cfg))

    if not targets:
        console.print("[yellow]No credentials to check.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Credential Check", show_lines=False, title_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("Auth URL")
    table.add_column("Username")
    table.add_column("Project")
    table.add_column("Status", no_wrap=True)
    table.add_column("Details")

    console.print()
    with console.status("[bold]Checking credentials..."):
        for label, cfg in targets:
            auth_url = cfg.get("auth_url", "?")
            username = cfg.get("username", "?")
            project = cfg.get("project_name") or cfg.get("project_id") or "?"

            if not config_is_complete(cfg):
                table.add_row(label, auth_url, username, project,
                              "[yellow]SKIP[/yellow]", "incomplete config")
                continue

            try:
                c = OrcaClient(cfg)
                td = c._token_data
                expires = td.get("expires_at", "")
                roles = [r.get("name", "?") for r in td.get("roles", [])]
                role_str = ", ".join(sorted(roles)) if roles else "no roles"

                detail = f"roles: {role_str}"
                if expires:
                    try:
                        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                        remaining = exp_dt - datetime.now(timezone.utc)
                        hours = int(remaining.total_seconds() // 3600)
                        detail += f" | token: {hours}h"
                    except (ValueError, TypeError):
                        pass

                table.add_row(label, auth_url, username, project,
                              "[green bold]OK[/green bold]", detail)
                c.close()
            except Exception as exc:
                msg = str(exc)[:80]
                table.add_row(label, auth_url, username, project,
                              "[red bold]FAIL[/red bold]", msg)

    console.print(table)
    console.print()


# ── token revoke ──────────────────────────────────────────────────────────

@auth.command("token-revoke")
@click.argument("token")
@click.pass_context
def auth_token_revoke(ctx: click.Context, token: str) -> None:
    """Revoke a token.

    \b
    Example:
      orca auth token-revoke <token-value>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(
        f"{client.identity_url}/auth/tokens",
        headers={"X-Subject-Token": token},
    )
    console.print("[green]Token revoked.[/green]")
