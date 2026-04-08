"""``shark cluster`` — manage Kubernetes clusters & templates (Magnum)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _magnum(client) -> str:
    return client.container_infra_url


# ══════════════════════════════════════════════════════════════════════════
#  Clusters
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def cluster(ctx: click.Context) -> None:
    """Manage Kubernetes clusters & cluster templates (Magnum)."""
    pass


@cluster.command("list")
@click.pass_context
def cluster_list(ctx: click.Context) -> None:
    """List clusters."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clusters")
    clusters = data.get("clusters", [])
    if not clusters:
        console.print("[yellow]No clusters found.[/yellow]")
        return

    table = Table(title="Clusters", show_lines=True)
    table.add_column("UUID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Masters", justify="right")
    table.add_column("Nodes", justify="right")
    table.add_column("Template")

    for c in clusters:
        table.add_row(
            c.get("uuid", ""),
            c.get("name", ""),
            c.get("status", ""),
            str(c.get("master_count", "")),
            str(c.get("node_count", "")),
            c.get("cluster_template_id", ""),
        )
    console.print(table)


@cluster.command("show")
@click.argument("cluster_id")
@click.pass_context
def cluster_show(ctx: click.Context, cluster_id: str) -> None:
    """Show cluster details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clusters/{cluster_id}")

    table = Table(title=f"Cluster {data.get('name', cluster_id)}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["uuid", "name", "status", "status_reason", "coe_version",
                "api_address", "master_count", "node_count",
                "master_addresses", "node_addresses",
                "cluster_template_id", "keypair", "stack_id",
                "create_timeout", "created_at", "updated_at"]:
        table.add_row(key, str(data.get(key, "")))
    console.print(table)


@cluster.command("create")
@click.argument("name")
@click.option("--template", "cluster_template_id", required=True, help="Cluster template UUID or name.")
@click.option("--node-count", type=int, default=1, show_default=True, help="Number of worker nodes.")
@click.option("--master-count", type=int, default=1, show_default=True, help="Number of master nodes.")
@click.option("--keypair", default=None, help="SSH keypair name.")
@click.option("--timeout", "create_timeout", type=int, default=60, show_default=True, help="Creation timeout (minutes).")
@click.option("--flavor", "flavor_id", default=None, help="Node flavor (overrides template).")
@click.option("--master-flavor", "master_flavor_id", default=None, help="Master flavor (overrides template).")
@click.pass_context
def cluster_create(ctx: click.Context, name: str, cluster_template_id: str,
                   node_count: int, master_count: int, keypair: str | None,
                   create_timeout: int, flavor_id: str | None,
                   master_flavor_id: str | None) -> None:
    """Create a Kubernetes cluster.

    \b
    Examples:
      shark cluster create my-k8s --template <template-id> --node-count 3
      shark cluster create prod --template <id> --master-count 3 --node-count 5 --keypair my-key
    """
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "name": name,
        "cluster_template_id": cluster_template_id,
        "node_count": node_count,
        "master_count": master_count,
        "create_timeout": create_timeout,
    }
    if keypair:
        body["keypair"] = keypair
    if flavor_id:
        body["flavor_id"] = flavor_id
    if master_flavor_id:
        body["master_flavor_id"] = master_flavor_id

    data = client.post(f"{_magnum(client)}/clusters", json=body)
    uuid = data.get("uuid", "") if data else ""
    console.print(f"[green]Cluster '{name}' creation started ({uuid}).[/green]")
    console.print("[dim]Use 'shark cluster show' to track progress.[/dim]")


@cluster.command("delete")
@click.argument("cluster_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cluster_delete(ctx: click.Context, cluster_id: str, yes: bool) -> None:
    """Delete a cluster."""
    if not yes:
        click.confirm(f"Delete cluster {cluster_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_magnum(client)}/clusters/{cluster_id}")
    console.print(f"[green]Cluster {cluster_id} deletion started.[/green]")


@cluster.command("resize")
@click.argument("cluster_id")
@click.option("--node-count", type=int, required=True, help="New number of worker nodes.")
@click.pass_context
def cluster_resize(ctx: click.Context, cluster_id: str, node_count: int) -> None:
    """Resize a cluster (change worker node count)."""
    client = ctx.find_object(SharkContext).ensure_client()
    body = [{"op": "replace", "path": "/node_count", "value": node_count}]
    client.patch(f"{_magnum(client)}/clusters/{cluster_id}",
                 json=body, content_type="application/json-patch+json")
    console.print(f"[green]Cluster {cluster_id} resize to {node_count} nodes started.[/green]")


@cluster.command("kubeconfig")
@click.argument("cluster_id")
@click.pass_context
def cluster_kubeconfig(ctx: click.Context, cluster_id: str) -> None:
    """Show the cluster API address and connection info."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clusters/{cluster_id}")

    api = data.get("api_address", "")
    status = data.get("status", "")
    name = data.get("name", cluster_id)

    if status != "CREATE_COMPLETE":
        console.print(f"[yellow]Cluster '{name}' is {status} — API may not be ready.[/yellow]")

    if api:
        console.print(f"[bold]Cluster:[/bold]  {name}")
        console.print(f"[bold]API URL:[/bold]  {api}")
        console.print(f"[bold]Status:[/bold]   {status}")
        console.print(f"\n[dim]Use 'shark cluster get-cert {cluster_id}' to get the CA certificate.[/dim]")
    else:
        console.print("[yellow]No API address available yet.[/yellow]")


# ══════════════════════════════════════════════════════════════════════════
#  Cluster Templates
# ══════════════════════════════════════════════════════════════════════════

@cluster.command("template-list")
@click.pass_context
def template_list(ctx: click.Context) -> None:
    """List cluster templates."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clustertemplates")
    templates = data.get("clustertemplates", [])
    if not templates:
        console.print("[yellow]No cluster templates found.[/yellow]")
        return

    table = Table(title="Cluster Templates", show_lines=True)
    table.add_column("UUID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("COE")
    table.add_column("Image")
    table.add_column("Network Driver")
    table.add_column("Public")

    for t in templates:
        table.add_row(
            t.get("uuid", ""),
            t.get("name", ""),
            t.get("coe", ""),
            t.get("image_id", ""),
            t.get("network_driver", "") or "—",
            str(t.get("public", "")),
        )
    console.print(table)


@cluster.command("template-show")
@click.argument("template_id")
@click.pass_context
def template_show(ctx: click.Context, template_id: str) -> None:
    """Show cluster template details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clustertemplates/{template_id}")

    table = Table(title=f"Template {data.get('name', template_id)}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["uuid", "name", "coe", "image_id", "keypair_id",
                "external_network_id", "fixed_network", "fixed_subnet",
                "network_driver", "volume_driver", "docker_volume_size",
                "server_type", "master_flavor_id", "flavor_id",
                "dns_nameserver", "public", "tls_disabled",
                "master_lb_enabled", "floating_ip_enabled",
                "labels", "created_at", "updated_at"]:
        val = data.get(key, "")
        table.add_row(key, str(val) if val is not None else "")
    console.print(table)


@cluster.command("template-create")
@click.argument("name")
@click.option("--image", "image_id", required=True, help="Base image UUID or name.")
@click.option("--external-network", "external_network_id", required=True, help="External network ID.")
@click.option("--coe", type=click.Choice(["kubernetes", "swarm", "mesos"]), default="kubernetes", show_default=True)
@click.option("--keypair", "keypair_id", default=None, help="SSH keypair name.")
@click.option("--flavor", "flavor_id", default=None, help="Node flavor.")
@click.option("--master-flavor", "master_flavor_id", default=None, help="Master flavor.")
@click.option("--network-driver", default=None, help="Network driver (flannel, calico, etc.).")
@click.option("--docker-volume-size", type=int, default=None, help="Docker volume size in GB.")
@click.option("--dns", "dns_nameserver", default="8.8.8.8", show_default=True, help="DNS nameserver.")
@click.option("--master-lb/--no-master-lb", "master_lb_enabled", default=True, show_default=True)
@click.option("--floating-ip/--no-floating-ip", "floating_ip_enabled", default=True, show_default=True)
@click.option("--label", "labels", multiple=True, help="Key=value label (repeatable). E.g. --label boot_volume_size=20")
@click.pass_context
def template_create(ctx: click.Context, name: str, image_id: str, external_network_id: str,
                    coe: str, keypair_id: str | None, flavor_id: str | None,
                    master_flavor_id: str | None, network_driver: str | None,
                    docker_volume_size: int | None, dns_nameserver: str,
                    master_lb_enabled: bool, floating_ip_enabled: bool,
                    labels: tuple[str, ...]) -> None:
    """Create a cluster template."""
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {
        "name": name,
        "image_id": image_id,
        "external_network_id": external_network_id,
        "coe": coe,
        "dns_nameserver": dns_nameserver,
        "master_lb_enabled": master_lb_enabled,
        "floating_ip_enabled": floating_ip_enabled,
    }
    if keypair_id:
        body["keypair_id"] = keypair_id
    if flavor_id:
        body["flavor_id"] = flavor_id
    if master_flavor_id:
        body["master_flavor_id"] = master_flavor_id
    if network_driver:
        body["network_driver"] = network_driver
    if docker_volume_size:
        body["docker_volume_size"] = docker_volume_size
    if labels:
        body["labels"] = dict(l.split("=", 1) for l in labels)

    data = client.post(f"{_magnum(client)}/clustertemplates", json=body)
    console.print(f"[green]Template '{data.get('name')}' ({data.get('uuid')}) created.[/green]")


@cluster.command("template-delete")
@click.argument("template_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def template_delete(ctx: click.Context, template_id: str, yes: bool) -> None:
    """Delete a cluster template."""
    if not yes:
        click.confirm(f"Delete template {template_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_magnum(client)}/clustertemplates/{template_id}")
    console.print(f"[green]Template {template_id} deleted.[/green]")
