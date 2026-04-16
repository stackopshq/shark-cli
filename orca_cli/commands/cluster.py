"""``orca cluster`` — manage Kubernetes clusters & templates (Magnum)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


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
@output_options
@click.pass_context
def cluster_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List clusters."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clusters")

    print_list(
        data.get("clusters", []),
        [
            ("UUID", "uuid", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("Masters", "master_count", {"justify": "right"}),
            ("Nodes", "node_count", {"justify": "right"}),
            ("Template", "cluster_template_id"),
        ],
        title="Clusters",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No clusters found.",
    )


@cluster.command("show")
@click.argument("cluster_id")
@output_options
@click.pass_context
def cluster_show(ctx: click.Context, cluster_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show cluster details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clusters/{cluster_id}")

    fields = [(key, str(data.get(key, ""))) for key in
              ["uuid", "name", "status", "status_reason", "coe_version",
               "api_address", "master_count", "node_count",
               "master_addresses", "node_addresses",
               "cluster_template_id", "keypair", "stack_id",
               "create_timeout", "created_at", "updated_at"]]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


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
      orca cluster create my-k8s --template <template-id> --node-count 3
      orca cluster create prod --template <id> --master-count 3 --node-count 5 --keypair my-key
    """
    client = ctx.find_object(OrcaContext).ensure_client()
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
    console.print("[dim]Use 'orca cluster show' to track progress.[/dim]")


@cluster.command("delete")
@click.argument("cluster_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cluster_delete(ctx: click.Context, cluster_id: str, yes: bool) -> None:
    """Delete a cluster."""
    if not yes:
        click.confirm(f"Delete cluster {cluster_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_magnum(client)}/clusters/{cluster_id}")
    console.print(f"[green]Cluster {cluster_id} deletion started.[/green]")


@cluster.command("resize")
@click.argument("cluster_id")
@click.option("--node-count", type=int, required=True, help="New number of worker nodes.")
@click.pass_context
def cluster_resize(ctx: click.Context, cluster_id: str, node_count: int) -> None:
    """Resize a cluster (change worker node count)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = [{"op": "replace", "path": "/node_count", "value": node_count}]
    client.patch(f"{_magnum(client)}/clusters/{cluster_id}",
                 json=body, content_type="application/json-patch+json")
    console.print(f"[green]Cluster {cluster_id} resize to {node_count} nodes started.[/green]")


@cluster.command("kubeconfig")
@click.argument("cluster_id")
@click.pass_context
def cluster_kubeconfig(ctx: click.Context, cluster_id: str) -> None:
    """Show the cluster API address and connection info."""
    client = ctx.find_object(OrcaContext).ensure_client()
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
        console.print(f"\n[dim]Use 'orca cluster get-cert {cluster_id}' to get the CA certificate.[/dim]")
    else:
        console.print("[yellow]No API address available yet.[/yellow]")


# ══════════════════════════════════════════════════════════════════════════
#  Cluster Templates
# ══════════════════════════════════════════════════════════════════════════

@cluster.command("template-list")
@output_options
@click.pass_context
def template_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List cluster templates."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clustertemplates")

    print_list(
        data.get("clustertemplates", []),
        [
            ("UUID", "uuid", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("COE", "coe"),
            ("Image", "image_id"),
            ("Network Driver", lambda t: t.get("network_driver", "") or "—"),
            ("Public", "public"),
        ],
        title="Cluster Templates",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No cluster templates found.",
    )


@cluster.command("template-show")
@click.argument("template_id")
@output_options
@click.pass_context
def template_show(ctx: click.Context, template_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show cluster template details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_magnum(client)}/clustertemplates/{template_id}")

    fields = [(key, str(data.get(key, "") if data.get(key) is not None else "")) for key in
              ["uuid", "name", "coe", "image_id", "keypair_id",
               "external_network_id", "fixed_network", "fixed_subnet",
               "network_driver", "volume_driver", "docker_volume_size",
               "server_type", "master_flavor_id", "flavor_id",
               "dns_nameserver", "public", "tls_disabled",
               "master_lb_enabled", "floating_ip_enabled",
               "labels", "created_at", "updated_at"]]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


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
    client = ctx.find_object(OrcaContext).ensure_client()
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
        body["labels"] = dict(item.split("=", 1) for item in labels)

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
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_magnum(client)}/clustertemplates/{template_id}")
    console.print(f"[green]Template {template_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Cluster upgrade
# ══════════════════════════════════════════════════════════════════════════

@cluster.command("upgrade")
@click.argument("cluster_id")
@click.option("--template-id", required=True,
              help="New cluster template ID to upgrade to.")
@click.option("--max-batch-size", type=int, default=1, show_default=True,
              help="Max number of nodes to upgrade simultaneously.")
@click.option("--nodegroup", default=None, help="Specific nodegroup to upgrade.")
@click.pass_context
def cluster_upgrade(ctx: click.Context, cluster_id: str, template_id: str,
                    max_batch_size: int, nodegroup: str | None) -> None:
    """Upgrade a cluster to a new template version."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"cluster_template": template_id, "max_batch_size": max_batch_size}
    if nodegroup:
        body["nodegroup"] = nodegroup
    client.post(f"{_magnum(client)}/clusters/{cluster_id}/actions/upgrade",
                json=body)
    console.print(f"[green]Cluster {cluster_id} upgrade started.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Node Groups
# ══════════════════════════════════════════════════════════════════════════

@cluster.command("nodegroup-list")
@click.argument("cluster_id")
@output_options
@click.pass_context
def nodegroup_list(ctx: click.Context, cluster_id: str, output_format: str,
                   columns: tuple[str, ...], fit_width: bool,
                   max_width: int | None, noindent: bool) -> None:
    """List node groups in a cluster."""
    client = ctx.find_object(OrcaContext).ensure_client()
    ngs = client.get(f"{_magnum(client)}/clusters/{cluster_id}/nodegroups").get(
        "nodegroups", []
    )
    print_list(
        ngs,
        [
            ("UUID", "uuid", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Role", "role"),
            ("Node Count", lambda n: str(n.get("node_count", 0)), {"justify": "right"}),
            ("Status", "status", {"style": "green"}),
            ("Flavor", "flavor_id"),
        ],
        title=f"Node Groups for cluster {cluster_id}",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No node groups found.",
    )


@cluster.command("nodegroup-show")
@click.argument("cluster_id")
@click.argument("nodegroup_id")
@output_options
@click.pass_context
def nodegroup_show(ctx: click.Context, cluster_id: str, nodegroup_id: str,
                   output_format: str, columns: tuple[str, ...],
                   fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show node group details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    ng = client.get(
        f"{_magnum(client)}/clusters/{cluster_id}/nodegroups/{nodegroup_id}"
    )
    fields = [(k, str(ng.get(k, "") or "")) for k in
              ["uuid", "name", "cluster_id", "role", "flavor_id", "image_id",
               "node_count", "min_node_count", "max_node_count",
               "status", "status_reason", "created_at", "updated_at"]]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@cluster.command("nodegroup-create")
@click.argument("cluster_id")
@click.option("--name", required=True, help="Node group name.")
@click.option("--flavor-id", required=True, help="Flavor ID for nodes.")
@click.option("--node-count", type=int, default=1, show_default=True,
              help="Initial number of nodes.")
@click.option("--min-node-count", type=int, default=None,
              help="Minimum node count (for autoscaling).")
@click.option("--max-node-count", type=int, default=None,
              help="Maximum node count (for autoscaling).")
@click.option("--role", default="worker", show_default=True,
              help="Node group role (worker/infra).")
@click.option("--image-id", default=None, help="Override image ID.")
@click.pass_context
def nodegroup_create(ctx: click.Context, cluster_id: str, name: str,
                     flavor_id: str, node_count: int,
                     min_node_count: int | None, max_node_count: int | None,
                     role: str, image_id: str | None) -> None:
    """Create a node group in a cluster."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {
        "name": name, "flavor_id": flavor_id,
        "node_count": node_count, "role": role,
    }
    if min_node_count is not None:
        body["min_node_count"] = min_node_count
    if max_node_count is not None:
        body["max_node_count"] = max_node_count
    if image_id:
        body["image_id"] = image_id
    ng = client.post(
        f"{_magnum(client)}/clusters/{cluster_id}/nodegroups", json=body
    )
    console.print(f"[green]Node group '{name}' created: {ng.get('uuid', '?')}[/green]")


@cluster.command("nodegroup-update")
@click.argument("cluster_id")
@click.argument("nodegroup_id")
@click.option("--node-count", type=int, default=None, help="New node count.")
@click.option("--min-node-count", type=int, default=None, help="New minimum node count.")
@click.option("--max-node-count", type=int, default=None, help="New maximum node count.")
@click.pass_context
def nodegroup_update(ctx: click.Context, cluster_id: str, nodegroup_id: str,
                     node_count: int | None, min_node_count: int | None,
                     max_node_count: int | None) -> None:
    """Update a node group (resize / autoscaling bounds)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    ops = []
    for path, val in [("/node_count", node_count),
                      ("/min_node_count", min_node_count),
                      ("/max_node_count", max_node_count)]:
        if val is not None:
            ops.append({"op": "replace", "path": path, "value": val})
    if not ops:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    client.patch(f"{_magnum(client)}/clusters/{cluster_id}/nodegroups/{nodegroup_id}",
                 json=ops)
    console.print(f"[green]Node group {nodegroup_id} updated.[/green]")


@cluster.command("nodegroup-delete")
@click.argument("cluster_id")
@click.argument("nodegroup_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def nodegroup_delete(ctx: click.Context, cluster_id: str, nodegroup_id: str,
                     yes: bool) -> None:
    """Delete a node group."""
    if not yes:
        click.confirm(f"Delete node group {nodegroup_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(
        f"{_magnum(client)}/clusters/{cluster_id}/nodegroups/{nodegroup_id}"
    )
    console.print(f"[green]Node group {nodegroup_id} deleted.[/green]")
