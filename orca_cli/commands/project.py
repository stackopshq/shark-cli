"""``orca project`` — manage projects (Keystone v3)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import APIError
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.services.dns import DnsService
from orca_cli.services.identity import IdentityService
from orca_cli.services.image import ImageService
from orca_cli.services.key_manager import KeyManagerService
from orca_cli.services.load_balancer import LoadBalancerService
from orca_cli.services.network import NetworkService
from orca_cli.services.object_store import ObjectStoreService
from orca_cli.services.orchestration import OrchestrationService
from orca_cli.services.server import ServerService
from orca_cli.services.volume import VolumeService


@click.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """Manage projects (Keystone v3)."""
    pass


@project.command("list")
@click.option("--domain", default=None, help="Filter by domain ID.")
@click.option("--user", "user_id", default=None, help="Filter by user ID.")
@click.option("--enabled/--disabled", default=None, help="Filter by enabled state.")
@output_options
@click.pass_context
def project_list(ctx, domain, user_id, enabled,
                 output_format, columns, fit_width, max_width, noindent):
    """List projects."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    params: dict = {}
    if domain:
        params["domain_id"] = domain
    if user_id:
        params["user_id"] = user_id
    if enabled is not None:
        params["enabled"] = str(enabled).lower()

    print_list(
        svc.find_projects(params=params or None),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Domain ID", "domain_id"),
            ("Description", lambda p: (p.get("description") or "")[:40]),
            ("Enabled", lambda p: "[green]yes[/green]" if p.get("enabled") else "[red]no[/red]"),
        ],
        title="Projects",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No projects found.",
    )


@project.command("show")
@click.argument("project_id")
@output_options
@click.pass_context
def project_show(ctx, project_id, output_format, columns, fit_width, max_width, noindent):
    """Show project details."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    p = svc.get_project(project_id)
    print_detail(
        [
            ("ID", p.get("id", "")),
            ("Name", p.get("name", "")),
            ("Domain ID", p.get("domain_id", "")),
            ("Description", p.get("description") or "—"),
            ("Enabled", "yes" if p.get("enabled") else "no"),
            ("Parent ID", p.get("parent_id") or "—"),
            ("Tags", ", ".join(p.get("tags", [])) or "—"),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@project.command("create")
@click.argument("name")
@click.option("--domain", "domain_id", default=None, help="Domain ID.")
@click.option("--description", default=None, help="Description.")
@click.option("--enable/--disable", "enabled", default=True, show_default=True)
@click.option("--tag", "tags", multiple=True, help="Tag (repeatable).")
@click.pass_context
def project_create(ctx, name, domain_id, description, enabled, tags):
    """Create a project."""
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    body: dict = {"name": name, "enabled": enabled}
    if domain_id:
        body["domain_id"] = domain_id
    if description:
        body["description"] = description
    if tags:
        body["tags"] = list(tags)

    p = svc.create_project(body)
    console.print(f"[green]Project '{p.get('name')}' ({p.get('id')}) created.[/green]")


@project.command("set")
@click.argument("project_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--enable/--disable", "enabled", default=None)
@click.pass_context
def project_set(ctx, project_id, name, description, enabled):
    """Update a project."""
    body: dict = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled

    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return

    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.update_project(project_id, body)
    console.print(f"[green]Project {project_id} updated.[/green]")


@project.command("delete")
@click.argument("project_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def project_delete(ctx, project_id, yes):
    """Delete a project."""
    if not yes:
        click.confirm(f"Delete project {project_id}?", abort=True)
    svc = IdentityService(ctx.find_object(OrcaContext).ensure_client())
    svc.delete_project(project_id)
    console.print(f"[green]Project {project_id} deleted.[/green]")


# ── project cleanup ───────────────────────────────────────────────────────────

CLEANUP_RESOURCE_TYPES = [
    "stack", "loadbalancer", "server", "floating-ip", "dns-zone",
    "router", "network", "security-group",
    "backup", "volume", "snapshot", "image", "secret", "container",
]

# Dependency-aware deletion order
DELETION_ORDER = [
    "stack", "loadbalancer", "server", "floating-ip", "dns-zone",
    "router", "network", "security-group",
    "backup", "volume", "snapshot", "image", "secret", "container",
]


def _parse_cutoff(created_before: str | None) -> datetime | None:
    if not created_before:
        return None
    try:
        return datetime.fromisoformat(created_before.replace("Z", "+00:00"))
    except ValueError as exc:
        raise click.BadParameter(
            f"Invalid datetime '{created_before}'. Expected YYYY-MM-DDTHH:MM:SS.",
            param_hint="--created-before",
        ) from exc


def _before_cutoff(resource: dict, cutoff: datetime | None) -> bool:
    """True when the resource was created before the cutoff (include it)."""
    if cutoff is None:
        return True
    created = resource.get("created_at") or resource.get("created") or ""
    if not created:
        return True  # unknown age → include
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return dt < cutoff
    except (ValueError, TypeError):
        return True


# device_owner values for ports attached to a router that need to be detached
# via remove_router_interface before the router can be deleted. Router gateway
# ports (network:router_gateway, network:router_centralized_snat) are released
# by clearing external_gateway_info instead.
_ROUTER_INTERFACE_OWNERS = (
    "network:router_interface",
    "network:router_interface_distributed",
    "network:ha_router_replicated_interface",
)


def _delete_router(client, rid: str) -> None:
    """Detach all router interfaces and clear the external gateway, then delete."""
    net_svc = NetworkService(client)

    # Clear external gateway (releases router_gateway / centralized_snat ports).
    try:
        net_svc.update_router(rid, {"external_gateway_info": None})
    except Exception:
        pass

    # Detach every router-interface port, regardless of legacy/DVR/HA flavor.
    try:
        ports = net_svc.find_ports(params={"device_id": rid})
    except Exception:
        ports = []
    for p in ports:
        owner = p.get("device_owner", "")
        if not any(owner.startswith(o) for o in _ROUTER_INTERFACE_OWNERS):
            continue
        try:
            net_svc.remove_router_interface(rid, {"port_id": p["id"]})
        except Exception:
            pass

    net_svc.delete_router(rid)


def _delete_network(client, nid: str) -> None:
    """Delete orphan/compute leftover ports, then delete the network."""
    net_svc = NetworkService(client)

    # Ports owned by Neutron itself (dhcp, router, floatingip, ha_*) are cleaned
    # up by their respective delete paths; we only remove truly orphaned ports
    # or stale compute VIFs whose server has already been deleted.
    try:
        ports = net_svc.find_ports(params={"network_id": nid})
    except Exception:
        ports = []
    for p in ports:
        owner = p.get("device_owner", "")
        if owner and not owner.startswith("compute:"):
            continue
        try:
            net_svc.delete_port(p["id"])
        except Exception:
            pass

    net_svc.delete(nid)


class Outcome(Enum):
    """Result of a single resource delete attempt.

    ALREADY_GONE distinguishes idempotent successes (the resource was
    deleted by a cascade — typical for volumes attached to a server with
    delete_on_termination=True) from real failures. BLOCKED flags
    dependency errors (409) separately from transport/server errors so
    the operator can retry cleanup without chasing a spurious red line.
    """

    SUCCESS = "success"
    ALREADY_GONE = "already_gone"
    BLOCKED = "blocked"
    FAILED = "failed"


_OUTCOME_MARKER = {
    Outcome.SUCCESS: "[green]✓[/green]",
    Outcome.ALREADY_GONE: "[cyan]~[/cyan]",
    Outcome.BLOCKED: "[yellow]⊘[/yellow]",
    Outcome.FAILED: "[red]✗[/red]",
}


def _classify_api_error(exc: APIError) -> Outcome:
    if exc.status_code == 404:
        return Outcome.ALREADY_GONE
    if exc.status_code == 409:
        return Outcome.BLOCKED
    return Outcome.FAILED


def _delete_one(client, rtype: str, rid: str, rname: str) -> Outcome:
    """Delete a single resource by type. Returns the classified outcome."""
    label = f"{rtype} {rname} ({rid})"
    try:
        if rtype == "stack":
            OrchestrationService(client).delete(rname, rid)
        elif rtype == "loadbalancer":
            LoadBalancerService(client).delete(rid, cascade=True)
        elif rtype == "server":
            ServerService(client).delete(rid)
        elif rtype == "floating-ip":
            NetworkService(client).delete_floating_ip(rid)
        elif rtype == "router":
            _delete_router(client, rid)
        elif rtype == "network":
            _delete_network(client, rid)
        elif rtype == "security-group":
            NetworkService(client).delete_security_group(rid)
        elif rtype == "volume":
            VolumeService(client).delete(rid, cascade=True)
        elif rtype == "snapshot":
            VolumeService(client).delete_snapshot(rid)
        elif rtype == "image":
            ImageService(client).delete(rid)
        elif rtype == "secret":
            KeyManagerService(client).delete_secret(rid)
        elif rtype == "backup":
            VolumeService(client).delete_backup(rid)
        elif rtype == "dns-zone":
            DnsService(client).delete_zone(rid)
        elif rtype == "container":
            # rid == container name for Swift; delete all objects first
            obj_svc = ObjectStoreService(client)
            try:
                for obj in obj_svc.find_objects(rid):
                    obj_name = obj.get("name", "")
                    if not obj_name:
                        continue
                    try:
                        obj_svc.delete_object(rid, obj_name)
                    except Exception:
                        pass
            except Exception:
                pass
            obj_svc.delete_container(rid)
        console.print(f"  {_OUTCOME_MARKER[Outcome.SUCCESS]} {label}")
        return Outcome.SUCCESS
    except APIError as exc:
        outcome = _classify_api_error(exc)
        if outcome is Outcome.ALREADY_GONE:
            console.print(
                f"  {_OUTCOME_MARKER[outcome]} {label} "
                f"[dim](already gone)[/dim]"
            )
        else:
            console.print(f"  {_OUTCOME_MARKER[outcome]} {label}: {exc}")
        return outcome
    except Exception as exc:
        console.print(f"  {_OUTCOME_MARKER[Outcome.FAILED]} {label}: {exc}")
        return Outcome.FAILED


@project.command("cleanup")
@click.option("--project", "target_project", default=None,
              help="Project name or ID to clean up (default: current auth project).")
@click.option("--dry-run", is_flag=True,
              help="List resources that would be deleted without deleting them.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--created-before", default=None, metavar="YYYY-MM-DDTHH:MM:SS",
              help="Only delete resources created before this datetime (UTC).")
@click.option("--skip", "skip_types", multiple=True,
              type=click.Choice(CLEANUP_RESOURCE_TYPES),
              help="Resource type to skip (repeatable).")
@click.pass_context
def project_cleanup(ctx, target_project, dry_run, yes, created_before, skip_types):  # noqa: C901
    """Delete ALL resources in a project in dependency order.

    Requires admin credentials when targeting a project other than the one
    used for authentication.

    \b
    Deletion order (respects dependencies):
      stacks → load-balancers → servers → floating-ips → dns-zones
      → routers (interfaces detached first) → networks → security-groups
      → backups → volumes → snapshots → images → secrets
      → swift containers (objects deleted first)

    \b
    Examples:
      orca project cleanup --dry-run
      orca project cleanup --project my-test-tenant --yes
      orca project cleanup --created-before 2024-01-01T00:00:00 --skip image
      orca project cleanup --skip stack --skip secret --yes
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    skip = set(skip_types)
    cutoff = _parse_cutoff(created_before)

    # ── Resolve the target project ID ────────────────────────────────────────
    ident_svc = IdentityService(client)
    if target_project:
        try:
            candidates = ident_svc.find_projects(
                params={"name": target_project},
            )
        except Exception:
            candidates = []
        if candidates:
            proj_id = candidates[0]["id"]
        else:
            try:
                p = ident_svc.get_project(target_project)
                proj_id = p.get("id", target_project)
            except Exception as exc:
                raise click.ClickException(f"Project '{target_project}' not found.") from exc
    else:
        proj_id = client._token_data.get("project", {}).get("id")
        if not proj_id:
            raise click.ClickException(
                "Could not determine current project. Use --project to specify one."
            )

    # ── Collect all resources ─────────────────────────────────────────────────
    resources: list[tuple[str, str, str]] = []  # (type, id, name)

    def add(rtype: str, items: list, name_key: str = "name") -> None:
        for r in items:
            if _before_cutoff(r, cutoff):
                resources.append((rtype, r["id"], r.get(name_key) or "—"))

    p_filter = {"project_id": proj_id}
    tenant_filter = {"tenant_id": proj_id}

    with console.status("[bold cyan]Scanning project resources…[/bold cyan]"):

        if "stack" not in skip:
            # Heat: auth token already scopes to the project; for other projects
            # pass project_id (requires admin + global_tenant).
            stack_params: dict = {}
            auth_proj = client._token_data.get("project", {}).get("id")
            if proj_id != auth_proj:
                stack_params = {"project_id": proj_id, "global_tenant": "true"}
            heat_svc = OrchestrationService(client)
            try:
                heat_stacks = heat_svc.find(params=stack_params or None)
            except Exception:
                heat_stacks = []
            add("stack", heat_stacks, name_key="stack_name")

        if "loadbalancer" not in skip:
            try:
                lbs = LoadBalancerService(client).find(params=p_filter)
            except Exception:
                lbs = []
            add("loadbalancer", lbs)

        if "server" not in skip:
            try:
                servers = ServerService(client).find_all(
                    params={"project_id": proj_id},
                )
            except Exception:
                servers = []
            add("server", servers)

        if "floating-ip" not in skip:
            try:
                fips = NetworkService(client).find_floating_ips(params=p_filter)
            except Exception:
                fips = []
            add("floating-ip", fips, name_key="floating_ip_address")

        if "dns-zone" not in skip:
            # Designate scopes zones to the auth token project by default.
            # For a different project, pass X-Auth-All-Projects + project_id.
            auth_proj = client._token_data.get("project", {}).get("id")
            dns_params: dict = {}
            dns_headers: dict = {}
            if proj_id != auth_proj:
                dns_params["project_id"] = proj_id
                dns_headers["X-Auth-All-Projects"] = "true"
            try:
                zones = DnsService(client).find_zones(
                    params=dns_params or None,
                    headers=dns_headers or None,
                )
                for z in zones:
                    if _before_cutoff(z, cutoff):
                        resources.append(("dns-zone", z["id"], z.get("name") or "—"))
            except Exception:
                pass

        net_svc = NetworkService(client)

        if "router" not in skip:
            try:
                routers = net_svc.find_routers(params=tenant_filter)
            except Exception:
                routers = []
            add("router", routers)

        if "network" not in skip:
            try:
                nets = net_svc.find(params=tenant_filter)
            except Exception:
                nets = []
            add("network", nets)

        if "security-group" not in skip:
            try:
                sgs = net_svc.find_security_groups(params=tenant_filter)
            except Exception:
                sgs = []
            add("security-group",
                [sg for sg in sgs if sg.get("name") != "default"])

        if "volume" not in skip:
            try:
                vols = VolumeService(client).find(params=p_filter)
            except Exception:
                vols = []
            add("volume", vols)

        if "snapshot" not in skip:
            try:
                snaps = VolumeService(client).find_snapshots(params=p_filter)
            except Exception:
                snaps = []
            add("snapshot", snaps)

        if "image" not in skip:
            try:
                imgs = ImageService(client).find(params={"owner": proj_id})
            except Exception:
                imgs = []
            add("image", imgs)

        if "backup" not in skip:
            try:
                backups = VolumeService(client).find_backups(params=p_filter)
            except Exception:
                backups = []
            add("backup", backups)

        if "secret" not in skip:
            try:
                secrets = KeyManagerService(client).find_secrets(params=p_filter)
                for s in secrets:
                    if not _before_cutoff(s, cutoff):
                        continue
                    href = s.get("secret_ref", "")
                    sid = href.rstrip("/").split("/")[-1]
                    resources.append(("secret", sid, s.get("name") or "—"))
            except Exception:
                pass

        if "container" not in skip:
            # Swift: GET {url}?format=json returns [{name, count, bytes}, ...]
            # Containers have no created_at so cutoff does not apply.
            try:
                for c in ObjectStoreService(client).find_containers():
                    name = c.get("name", "")
                    if name:
                        # Use name as both id and display name (Swift has no UUID)
                        resources.append(("container", name, name))
            except Exception:
                pass

    # ── Display ───────────────────────────────────────────────────────────────
    if not resources:
        console.print("[bold green]No resources found in project.[/bold green]")
        return

    from rich.table import Table
    tbl = Table(
        title=f"Resources to delete in project {proj_id} ({len(resources)})",
        show_lines=False,
    )
    tbl.add_column("Type", style="bold")
    tbl.add_column("ID", style="cyan", no_wrap=True)
    tbl.add_column("Name")
    for rtype, rid, rname in resources:
        tbl.add_row(rtype, rid, rname)
    console.print()
    console.print(tbl)
    console.print()

    if dry_run:
        console.print(f"[dim]Dry run — {len(resources)} resource(s) would be deleted.[/dim]")
        return

    if not yes:
        click.confirm(
            f"Delete {len(resources)} resource(s) from project {proj_id}?",
            abort=True,
        )

    # ── Delete in dependency order ────────────────────────────────────────────
    by_type: dict[str, list[tuple[str, str]]] = {}
    for rtype, rid, rname in resources:
        by_type.setdefault(rtype, []).append((rid, rname))

    tally: dict[Outcome, int] = {o: 0 for o in Outcome}
    for rtype in DELETION_ORDER:
        for rid, rname in by_type.get(rtype, []):
            tally[_delete_one(client, rtype, rid, rname)] += 1

    parts = [
        f"[green]{tally[Outcome.SUCCESS]} deleted[/green]",
        f"[cyan]{tally[Outcome.ALREADY_GONE]} already gone[/cyan]",
        f"[yellow]{tally[Outcome.BLOCKED]} blocked[/yellow]",
        f"[red]{tally[Outcome.FAILED]} failed[/red]",
    ]
    console.print(f"\n[bold]{' · '.join(parts)}[/bold] (of {len(resources)})")
