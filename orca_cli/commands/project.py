"""``orca project`` — manage projects (Keystone v3)."""

from __future__ import annotations

from datetime import datetime, timezone

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.exceptions import APIError
from orca_cli.core.output import output_options, print_list, print_detail, console


def _iam(client) -> str:
    return client.identity_url


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
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if domain:
        params["domain_id"] = domain
    if user_id:
        params["user_id"] = user_id
    if enabled is not None:
        params["enabled"] = str(enabled).lower()

    data = client.get(f"{_iam(client)}/v3/projects", params=params)
    print_list(
        data.get("projects", []),
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
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_iam(client)}/v3/projects/{project_id}")
    p = data.get("project", data)
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
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name, "enabled": enabled}
    if domain_id:
        body["domain_id"] = domain_id
    if description:
        body["description"] = description
    if tags:
        body["tags"] = list(tags)

    data = client.post(f"{_iam(client)}/v3/projects", json={"project": body})
    p = data.get("project", data)
    console.print(f"[green]Project '{p.get('name')}' ({p.get('id')}) created.[/green]")


@project.command("set")
@click.argument("project_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--enable/--disable", "enabled", default=None)
@click.pass_context
def project_set(ctx, project_id, name, description, enabled):
    """Update a project."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled

    if not body:
        console.print("[yellow]Nothing to update.[/yellow]")
        return

    client.patch(f"{_iam(client)}/v3/projects/{project_id}", json={"project": body})
    console.print(f"[green]Project {project_id} updated.[/green]")


@project.command("delete")
@click.argument("project_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def project_delete(ctx, project_id, yes):
    """Delete a project."""
    if not yes:
        click.confirm(f"Delete project {project_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_iam(client)}/v3/projects/{project_id}")
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
    except ValueError:
        raise click.BadParameter(
            f"Invalid datetime '{created_before}'. Expected YYYY-MM-DDTHH:MM:SS.",
            param_hint="--created-before",
        )


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


def _collect(client, url: str, key: str, params: dict | None = None) -> list:
    """Fetch a resource list silently (returns [] if service unavailable)."""
    try:
        return client.get(url, params=params).get(key, [])
    except Exception:
        return []


def _delete_one(client, rtype: str, rid: str, rname: str) -> bool:
    """Delete a single resource by type. Returns True on success."""
    label = f"{rtype} {rname} ({rid})"
    try:
        if rtype == "stack":
            client.delete(f"{client.orchestration_url}/stacks/{rname}/{rid}")
        elif rtype == "loadbalancer":
            client.delete(
                f"{client.load_balancer_url}/v2/lbaas/loadbalancers/{rid}?cascade=true"
            )
        elif rtype == "server":
            client.delete(f"{client.compute_url}/servers/{rid}")
        elif rtype == "floating-ip":
            client.delete(f"{client.network_url}/v2.0/floatingips/{rid}")
        elif rtype == "router":
            # Detach all subnet interfaces before deleting
            ports = _collect(
                client, f"{client.network_url}/v2.0/ports", "ports",
                params={"device_id": rid, "device_owner": "network:router_interface"},
            )
            for p in ports:
                try:
                    client.put(
                        f"{client.network_url}/v2.0/routers/{rid}/remove_router_interface",
                        json={"port_id": p["id"]},
                    )
                except Exception:
                    pass
            client.delete(f"{client.network_url}/v2.0/routers/{rid}")
        elif rtype == "network":
            client.delete(f"{client.network_url}/v2.0/networks/{rid}")
        elif rtype == "security-group":
            client.delete(f"{client.network_url}/v2.0/security-groups/{rid}")
        elif rtype == "volume":
            client.delete(f"{client.volume_url}/volumes/{rid}?cascade=true")
        elif rtype == "snapshot":
            client.delete(f"{client.volume_url}/snapshots/{rid}")
        elif rtype == "image":
            client.delete(f"{client.image_url}/v2/images/{rid}")
        elif rtype == "secret":
            client.delete(f"{client.key_manager_url}/v1/secrets/{rid}")
        elif rtype == "backup":
            client.delete(f"{client.volume_url}/backups/{rid}")
        elif rtype == "dns-zone":
            client.delete(f"{client.dns_url}/v2/zones/{rid}")
        elif rtype == "container":
            # rid == container name for Swift; delete all objects first
            base = client.object_store_url
            try:
                objects = client.get(
                    f"{base}/{rid}", params={"format": "json"}
                )
                if isinstance(objects, list):
                    for obj in objects:
                        obj_name = obj.get("name", obj) if isinstance(obj, dict) else obj
                        try:
                            client.delete(f"{base}/{rid}/{obj_name}")
                        except Exception:
                            pass
            except Exception:
                pass
            client.delete(f"{base}/{rid}")
        console.print(f"  [green]✓[/green] {label}")
        return True
    except APIError as exc:
        console.print(f"  [red]✗[/red] {label}: {exc}")
        return False
    except Exception as exc:
        console.print(f"  [red]✗[/red] {label}: {exc}")
        return False


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
def project_cleanup(ctx, target_project, dry_run, yes, created_before, skip_types):
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
    if target_project:
        candidates = _collect(client, f"{_iam(client)}/v3/projects", "projects",
                              params={"name": target_project})
        if candidates:
            proj_id = candidates[0]["id"]
        else:
            try:
                data = client.get(f"{_iam(client)}/v3/projects/{target_project}")
                proj_id = data.get("project", {}).get("id", target_project)
            except Exception:
                raise click.ClickException(f"Project '{target_project}' not found.")
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
            add("stack",
                _collect(client, f"{client.orchestration_url}/stacks", "stacks",
                         params=stack_params or None),
                name_key="stack_name")

        if "loadbalancer" not in skip:
            add("loadbalancer",
                _collect(client,
                         f"{client.load_balancer_url}/v2/lbaas/loadbalancers",
                         "loadbalancers", params=p_filter))

        if "server" not in skip:
            add("server",
                _collect(client, f"{client.compute_url}/servers/detail", "servers",
                         params={"project_id": proj_id, "limit": 1000}))

        if "floating-ip" not in skip:
            add("floating-ip",
                _collect(client, f"{client.network_url}/v2.0/floatingips",
                         "floatingips", params=p_filter),
                name_key="floating_ip_address")

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
                dns_data = client.get(
                    f"{client.dns_url}/v2/zones",
                    params=dns_params or None,
                    headers=dns_headers or None,
                )
                for z in dns_data.get("zones", []):
                    if _before_cutoff(z, cutoff):
                        resources.append(("dns-zone", z["id"], z.get("name") or "—"))
            except Exception:
                pass

        if "router" not in skip:
            add("router",
                _collect(client, f"{client.network_url}/v2.0/routers",
                         "routers", params=tenant_filter))

        if "network" not in skip:
            add("network",
                _collect(client, f"{client.network_url}/v2.0/networks",
                         "networks", params=tenant_filter))

        if "security-group" not in skip:
            add("security-group",
                [sg for sg in _collect(client,
                                        f"{client.network_url}/v2.0/security-groups",
                                        "security_groups", params=tenant_filter)
                 if sg.get("name") != "default"])

        if "volume" not in skip:
            add("volume",
                _collect(client, f"{client.volume_url}/volumes/detail",
                         "volumes", params=p_filter))

        if "snapshot" not in skip:
            add("snapshot",
                _collect(client, f"{client.volume_url}/snapshots/detail",
                         "snapshots", params=p_filter))

        if "image" not in skip:
            add("image",
                _collect(client, f"{client.image_url}/v2/images",
                         "images", params={"owner": proj_id}))

        if "backup" not in skip:
            add("backup",
                _collect(client, f"{client.volume_url}/backups/detail",
                         "backups", params=p_filter))

        if "secret" not in skip:
            try:
                sec_data = client.get(f"{client.key_manager_url}/v1/secrets",
                                      params=p_filter)
                for s in sec_data.get("secrets", []):
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
                containers = client.get(
                    f"{client.object_store_url}", params={"format": "json"}
                )
                if isinstance(containers, list):
                    for c in containers:
                        name = c.get("name", "") if isinstance(c, dict) else str(c)
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

    success = 0
    for rtype in DELETION_ORDER:
        for rid, rname in by_type.get(rtype, []):
            if _delete_one(client, rtype, rid, rname):
                success += 1

    console.print(f"\n[bold]{success}/{len(resources)} resources deleted.[/bold]")
