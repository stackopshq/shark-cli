"""``orca placement`` — manage OpenStack Placement resources."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list
from orca_cli.core.validators import validate_id


def _url(client) -> str:
    return client.placement_url


def _ph() -> dict:
    """Return the Placement API microversion header required for most endpoints."""
    return {"OpenStack-API-Version": "placement 1.6"}


# ── Root group ───────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def placement(ctx: click.Context) -> None:
    """Manage Placement resources (resource providers, classes, traits, etc.)."""


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Providers
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-provider-list")
@click.option("--name", default=None, help="Filter by name.")
@click.option("--uuid", default=None, help="Filter by UUID.")
@click.option("--in-tree", default=None, metavar="UUID", help="Limit to providers in this tree.")
@output_options
@click.pass_context
def rp_list(ctx, name, uuid, in_tree, output_format, columns, fit_width, max_width, noindent):
    """List resource providers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if name:
        params["name"] = name
    if uuid:
        params["uuid"] = uuid
    if in_tree:
        params["in_tree"] = in_tree
    data = client.get(f"{_url(client)}/resource_providers", params=params)
    items = data.get("resource_providers", [])
    if not items:
        console.print("No resource providers found.")
        return
    col_defs = [
        ("UUID", "uuid"),
        ("Name", "name"),
        ("Generation", "generation"),
        ("Parent UUID", "parent_provider_uuid"),
    ]
    print_list(items, col_defs, title="Resource Providers",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-show")
@click.argument("uuid", callback=validate_id)
@output_options
@click.pass_context
def rp_show(ctx, uuid, output_format, columns, fit_width, max_width, noindent):
    """Show a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_providers/{uuid}")
    fields = [
        ("UUID", data.get("uuid", "")),
        ("Name", data.get("name", "")),
        ("Generation", data.get("generation", "")),
        ("Parent UUID", data.get("parent_provider_uuid", "")),
        ("Root UUID", data.get("root_provider_uuid", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-create")
@click.argument("name")
@click.option("--uuid", default=None, help="Explicit UUID for the new provider.")
@click.option("--parent-uuid", default=None,
              help="UUID of the parent provider.")
@output_options
@click.pass_context
def rp_create(ctx, name, uuid, parent_uuid, output_format, columns, fit_width, max_width, noindent):
    """Create a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"name": name}
    if uuid:
        body["uuid"] = uuid
    if parent_uuid:
        body["parent_provider_uuid"] = parent_uuid
    data = client.post(f"{_url(client)}/resource_providers", json=body)
    fields = [
        ("UUID", data.get("uuid", "")),
        ("Name", data.get("name", "")),
        ("Generation", data.get("generation", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-set")
@click.argument("uuid", callback=validate_id)
@click.option("--name", default=None, help="New name.")
@click.option("--parent-uuid", default=None, help="New parent provider UUID.")
@click.pass_context
def rp_set(ctx, uuid, name, parent_uuid):
    """Update a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {}
    if name:
        body["name"] = name
    if parent_uuid:
        body["parent_provider_uuid"] = parent_uuid
    if not body:
        console.print("Nothing to update.")
        return
    client.put(f"{_url(client)}/resource_providers/{uuid}", json=body)
    console.print(f"Resource provider [bold]{uuid}[/bold] updated.")


@placement.command("resource-provider-delete")
@click.argument("uuid", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rp_delete(ctx, uuid, yes):
    """Delete a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete resource provider {uuid}?", abort=True)
    client.delete(f"{_url(client)}/resource_providers/{uuid}")
    console.print(f"Resource provider [bold]{uuid}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Inventories
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-provider-inventory-list")
@click.argument("uuid", callback=validate_id)
@output_options
@click.pass_context
def rp_inventory_list(ctx, uuid, output_format, columns, fit_width, max_width, noindent):
    """List inventories for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_providers/{uuid}/inventories")
    raw = data.get("inventories", {})
    items = [{"resource_class": rc, **vals} for rc, vals in raw.items()]
    if not items:
        console.print("No inventories found.")
        return
    col_defs = [
        ("Resource Class", "resource_class"),
        ("Total", "total"),
        ("Reserved", "reserved"),
        ("Min Unit", "min_unit"),
        ("Max Unit", "max_unit"),
        ("Step Size", "step_size"),
        ("Alloc Ratio", "allocation_ratio"),
    ]
    print_list(items, col_defs, title=f"Inventories for {uuid}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-inventory-set")
@click.argument("uuid", callback=validate_id)
@click.argument("resource_class")
@click.option("--total", type=int, required=True, help="Total inventory units.")
@click.option("--reserved", type=int, default=0, show_default=True)
@click.option("--min-unit", type=int, default=1, show_default=True)
@click.option("--max-unit", type=int, default=None)
@click.option("--step-size", type=int, default=1, show_default=True)
@click.option("--allocation-ratio", type=float, default=1.0, show_default=True)
@click.pass_context
def rp_inventory_set(ctx, uuid, resource_class, total, reserved,
                     min_unit, max_unit, step_size, allocation_ratio):
    """Create or update a single inventory for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    # Fetch current generation
    rp = client.get(f"{_url(client)}/resource_providers/{uuid}")
    body = {
        "resource_provider_generation": rp.get("generation", 0),
        "total": total,
        "reserved": reserved,
        "min_unit": min_unit,
        "max_unit": max_unit if max_unit is not None else total,
        "step_size": step_size,
        "allocation_ratio": allocation_ratio,
    }
    client.put(f"{_url(client)}/resource_providers/{uuid}/inventories/{resource_class}",
               json=body)
    console.print(f"Inventory [bold]{resource_class}[/bold] set for provider [bold]{uuid}[/bold].")


@placement.command("resource-provider-inventory-delete")
@click.argument("uuid", callback=validate_id)
@click.argument("resource_class")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rp_inventory_delete(ctx, uuid, resource_class, yes):
    """Delete an inventory for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete inventory {resource_class} for {uuid}?", abort=True)
    client.delete(f"{_url(client)}/resource_providers/{uuid}/inventories/{resource_class}")
    console.print(f"Inventory [bold]{resource_class}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Usages
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-provider-usage")
@click.argument("uuid", callback=validate_id)
@output_options
@click.pass_context
def rp_usage(ctx, uuid, output_format, columns, fit_width, max_width, noindent):
    """Show usages for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_providers/{uuid}/usages")
    raw = data.get("usages", {})
    items = [{"resource_class": rc, "usage": used} for rc, used in raw.items()]
    if not items:
        console.print("No usages found.")
        return
    col_defs = [("Resource Class", "resource_class"), ("Usage", "usage")]
    print_list(items, col_defs, title=f"Usages for {uuid}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("usage-list")
@click.option("--project-id", default=None, help="Filter by project UUID.")
@click.option("--user-id", default=None, help="Filter by user UUID.")
@output_options
@click.pass_context
def usage_list(ctx, project_id, user_id, output_format, columns, fit_width, max_width, noindent):
    """Show aggregated usages by project/user."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if project_id:
        params["project_id"] = project_id
    if user_id:
        params["user_id"] = user_id
    data = client.get(f"{_url(client)}/usages", params=params, headers=_ph())
    raw = data.get("usages", {})
    items = [{"resource_class": rc, "usage": used} for rc, used in raw.items()]
    if not items:
        console.print("No usages found.")
        return
    col_defs = [("Resource Class", "resource_class"), ("Usage", "usage")]
    print_list(items, col_defs, title="Usages",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Classes
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-class-list")
@output_options
@click.pass_context
def rc_list(ctx, output_format, columns, fit_width, max_width, noindent):
    """List resource classes."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_classes", headers=_ph())
    items = data.get("resource_classes", [])
    if not items:
        console.print("No resource classes found.")
        return
    col_defs = [("Name", "name")]
    print_list(items, col_defs, title="Resource Classes",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-class-show")
@click.argument("name")
@click.pass_context
def rc_show(ctx, name):
    """Show a resource class."""
    client = ctx.find_object(OrcaContext).ensure_client()
    # Standard classes return 204 on GET; custom classes return 200 with links.
    # We just confirm existence via GET.
    client.get(f"{_url(client)}/resource_classes/{name}", headers=_ph())
    console.print(f"Resource class [bold]{name}[/bold] exists.")


@placement.command("resource-class-create")
@click.argument("name")
@click.pass_context
def rc_create(ctx, name):
    """Create a custom resource class (must start with CUSTOM_)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{_url(client)}/resource_classes/{name}", json={}, headers=_ph())
    console.print(f"Resource class [bold]{name}[/bold] created.")


@placement.command("resource-class-delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rc_delete(ctx, name, yes):
    """Delete a custom resource class."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete resource class {name}?", abort=True)
    client.delete(f"{_url(client)}/resource_classes/{name}", headers=_ph())
    console.print(f"Resource class [bold]{name}[/bold] deleted.")


# ══════════════════════════════════════════════════════════════════════════════
#  Traits
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("trait-list")
@click.option("--name", default=None, help="Filter traits by name prefix.")
@click.option("--associated", is_flag=True, default=False,
              help="Only traits associated with a resource provider.")
@output_options
@click.pass_context
def trait_list(ctx, name, associated, output_format, columns, fit_width, max_width, noindent):
    """List traits."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {}
    if name:
        params["name"] = name
    if associated:
        params["associated"] = "true"
    data = client.get(f"{_url(client)}/traits", params=params, headers=_ph())
    raw = data.get("traits", [])
    items = [{"name": t} for t in raw]
    if not items:
        console.print("No traits found.")
        return
    col_defs = [("Name", "name")]
    print_list(items, col_defs, title="Traits",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("trait-create")
@click.argument("name")
@click.pass_context
def trait_create(ctx, name):
    """Create a custom trait (must start with CUSTOM_)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{_url(client)}/traits/{name}", json={}, headers=_ph())
    console.print(f"Trait [bold]{name}[/bold] created.")


@placement.command("trait-delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def trait_delete(ctx, name, yes):
    """Delete a custom trait."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete trait {name}?", abort=True)
    client.delete(f"{_url(client)}/traits/{name}", headers=_ph())
    console.print(f"Trait [bold]{name}[/bold] deleted.")


@placement.command("resource-provider-trait-list")
@click.argument("uuid", callback=validate_id)
@output_options
@click.pass_context
def rp_trait_list(ctx, uuid, output_format, columns, fit_width, max_width, noindent):
    """List traits associated with a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_providers/{uuid}/traits", headers=_ph())
    raw = data.get("traits", [])
    items = [{"name": t} for t in raw]
    if not items:
        console.print("No traits found.")
        return
    col_defs = [("Name", "name")]
    print_list(items, col_defs, title=f"Traits for {uuid}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-trait-set")
@click.argument("uuid", callback=validate_id)
@click.argument("traits", nargs=-1, required=True)
@click.pass_context
def rp_trait_set(ctx, uuid, traits):
    """Set (replace) traits on a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    rp = client.get(f"{_url(client)}/resource_providers/{uuid}", headers=_ph())
    body = {
        "resource_provider_generation": rp.get("generation", 0),
        "traits": list(traits),
    }
    client.put(f"{_url(client)}/resource_providers/{uuid}/traits", json=body, headers=_ph())
    console.print(f"Traits set on [bold]{uuid}[/bold].")


@placement.command("resource-provider-trait-delete")
@click.argument("uuid", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rp_trait_delete(ctx, uuid, yes):
    """Remove all traits from a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Remove all traits from {uuid}?", abort=True)
    client.delete(f"{_url(client)}/resource_providers/{uuid}/traits", headers=_ph())
    console.print(f"All traits removed from [bold]{uuid}[/bold].")


# ══════════════════════════════════════════════════════════════════════════════
#  Allocations
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("allocation-show")
@click.argument("consumer_uuid", callback=validate_id)
@output_options
@click.pass_context
def allocation_show(ctx, consumer_uuid, output_format, columns, fit_width, max_width, noindent):
    """Show allocations for a consumer."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/allocations/{consumer_uuid}")
    allocs = data.get("allocations", {})
    items = []
    for rp_uuid, val in allocs.items():
        for rc, amount in val.get("resources", {}).items():
            items.append({"resource_provider": rp_uuid, "resource_class": rc, "amount": amount})
    if not items:
        console.print("No allocations found.")
        return
    col_defs = [
        ("Resource Provider", "resource_provider"),
        ("Resource Class", "resource_class"),
        ("Amount", "amount"),
    ]
    print_list(items, col_defs, title=f"Allocations for {consumer_uuid}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("allocation-delete")
@click.argument("consumer_uuid", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def allocation_delete(ctx, consumer_uuid, yes):
    """Delete all allocations for a consumer."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete all allocations for consumer {consumer_uuid}?", abort=True)
    client.delete(f"{_url(client)}/allocations/{consumer_uuid}")
    console.print(f"Allocations for [bold]{consumer_uuid}[/bold] deleted.")


@placement.command("allocation-set")
@click.argument("consumer_uuid", callback=validate_id)
@click.option("--resource-provider", "rp_uuid", required=True, callback=validate_id,
              help="Resource provider UUID.")
@click.option("--resource", "resources", multiple=True, metavar="CLASS=AMOUNT",
              required=True, help="Resource class and amount, e.g. VCPU=4. Repeatable.")
@click.option("--project-id", required=True, help="Consumer project UUID.")
@click.option("--user-id", required=True, help="Consumer user UUID.")
@click.pass_context
def allocation_set(ctx, consumer_uuid, rp_uuid, resources, project_id, user_id):
    """Set (replace) allocations for a consumer against a single resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    parsed: dict[str, int] = {}
    for item in resources:
        if "=" not in item:
            raise click.BadParameter(f"Expected CLASS=AMOUNT, got '{item}'.", param_hint="--resource")
        rc, _, amount = item.partition("=")
        try:
            parsed[rc.strip()] = int(amount.strip())
        except ValueError:
            raise click.BadParameter(f"Amount must be an integer, got '{amount}'.", param_hint="--resource")
    body = {
        "allocations": {rp_uuid: {"resources": parsed}},
        "project_id": project_id,
        "user_id": user_id,
    }
    client.put(f"{_url(client)}/allocations/{consumer_uuid}", json=body)
    console.print(f"Allocations for consumer [bold]{consumer_uuid}[/bold] set.")


# ══════════════════════════════════════════════════════════════════════════════
#  Allocation Candidates
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("allocation-candidate-list")
@click.option("--resource", "resources", multiple=True, metavar="CLASS=AMOUNT",
              required=True, help="Requested resource, e.g. VCPU=4. Repeatable.")
@click.option("--required", "required_traits", multiple=True, metavar="TRAIT",
              help="Required trait. Repeatable.")
@click.option("--forbidden", "forbidden_traits", multiple=True, metavar="TRAIT",
              help="Forbidden trait. Repeatable.")
@click.option("--limit", type=int, default=None, help="Max number of candidates.")
@output_options
@click.pass_context
def allocation_candidate_list(ctx, resources, required_traits, forbidden_traits, limit,
                               output_format, columns, fit_width, max_width, noindent):
    """List allocation candidates for the requested resources."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    for item in resources:
        if "=" not in item:
            raise click.BadParameter(f"Expected CLASS=AMOUNT, got '{item}'.", param_hint="--resource")
        rc, _, amount = item.partition("=")
        params[f"resources"] = params.get("resources", "") + (
            "," if params.get("resources") else ""
        ) + f"{rc.strip()}:{amount.strip()}"
    if required_traits:
        params["required"] = ",".join(required_traits)
    if forbidden_traits:
        params["forbidden"] = ",".join(f"!{t}" for t in forbidden_traits)
    if limit:
        params["limit"] = limit
    data = client.get(f"{_url(client)}/allocation_candidates", params=params)
    candidates = data.get("allocation_requests", [])
    if not candidates:
        console.print("No allocation candidates found.")
        return
    # Flatten for display: one row per (candidate_index, provider, resource_class, amount)
    items = []
    for i, req in enumerate(candidates):
        for rp_uuid, val in req.get("allocations", {}).items():
            for rc, amount in val.get("resources", {}).items():
                items.append({
                    "candidate": i + 1,
                    "resource_provider": rp_uuid,
                    "resource_class": rc,
                    "amount": amount,
                })
    col_defs = [
        ("#", "candidate"),
        ("Resource Provider", "resource_provider"),
        ("Resource Class", "resource_class"),
        ("Amount", "amount"),
    ]
    print_list(items, col_defs, title="Allocation Candidates",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


# ══════════════════════════════════════════════════════════════════════════════
#  Resource Provider Aggregates
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-provider-aggregate-list")
@click.argument("uuid", callback=validate_id)
@output_options
@click.pass_context
def rp_aggregate_list(ctx, uuid, output_format, columns, fit_width, max_width, noindent):
    """List aggregates associated with a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_url(client)}/resource_providers/{uuid}/aggregates")
    raw = data.get("aggregates", [])
    items = [{"uuid": agg} for agg in raw]
    if not items:
        console.print("No aggregates found.")
        return
    col_defs = [("UUID", "uuid")]
    print_list(items, col_defs, title=f"Aggregates for {uuid}",
               output_format=output_format, columns=columns,
               fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-aggregate-set")
@click.argument("uuid", callback=validate_id)
@click.argument("aggregates", nargs=-1, required=True)
@click.pass_context
def rp_aggregate_set(ctx, uuid, aggregates):
    """Set (replace) aggregates on a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    rp = client.get(f"{_url(client)}/resource_providers/{uuid}")
    body = {
        "aggregates": list(aggregates),
        "resource_provider_generation": rp.get("generation", 0),
    }
    client.put(f"{_url(client)}/resource_providers/{uuid}/aggregates", json=body)
    console.print(f"Aggregates set on [bold]{uuid}[/bold].")


@placement.command("resource-provider-aggregate-delete")
@click.argument("uuid", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rp_aggregate_delete(ctx, uuid, yes):
    """Remove all aggregate associations from a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Remove all aggregates from {uuid}?", abort=True)
    rp = client.get(f"{_url(client)}/resource_providers/{uuid}")
    body = {
        "aggregates": [],
        "resource_provider_generation": rp.get("generation", 0),
    }
    client.put(f"{_url(client)}/resource_providers/{uuid}/aggregates", json=body)
    console.print(f"All aggregates removed from [bold]{uuid}[/bold].")


# ══════════════════════════════════════════════════════════════════════════════
#  Inventory — show single / bulk set / bulk delete
# ══════════════════════════════════════════════════════════════════════════════

@placement.command("resource-provider-inventory-show")
@click.argument("uuid", callback=validate_id)
@click.argument("resource_class")
@output_options
@click.pass_context
def rp_inventory_show(ctx, uuid, resource_class, output_format, columns, fit_width, max_width, noindent):
    """Show a single inventory for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(
        f"{_url(client)}/resource_providers/{uuid}/inventories/{resource_class}"
    )
    fields = [
        ("Resource Class", resource_class),
        ("Total", data.get("total", "")),
        ("Reserved", data.get("reserved", "")),
        ("Min Unit", data.get("min_unit", "")),
        ("Max Unit", data.get("max_unit", "")),
        ("Step Size", data.get("step_size", "")),
        ("Allocation Ratio", data.get("allocation_ratio", "")),
    ]
    print_detail(fields,
                 output_format=output_format, columns=columns,
                 fit_width=fit_width, max_width=max_width, noindent=noindent)


@placement.command("resource-provider-inventory-delete-all")
@click.argument("uuid", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rp_inventory_delete_all(ctx, uuid, yes):
    """Delete all inventories for a resource provider."""
    client = ctx.find_object(OrcaContext).ensure_client()
    if not yes:
        click.confirm(f"Delete all inventories for {uuid}?", abort=True)
    client.delete(f"{_url(client)}/resource_providers/{uuid}/inventories")
    console.print(f"All inventories deleted for [bold]{uuid}[/bold].")
