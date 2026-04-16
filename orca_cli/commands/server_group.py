"""``orca server-group`` — manage server groups (Nova)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console


def _nova(client) -> str:
    return client.compute_url


@click.group(name="server-group")
@click.pass_context
def server_group(ctx: click.Context) -> None:
    """Manage server groups (Nova)."""
    pass


@server_group.command("list")
@click.option("--all", "all_projects", is_flag=True, help="List server groups for all projects (admin).")
@output_options
@click.pass_context
def server_group_list(ctx, all_projects, output_format, columns, fit_width, max_width, noindent):
    """List server groups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params = {"all_projects": "true"} if all_projects else {}
    data = client.get(f"{_nova(client)}/os-server-groups", params=params)
    print_list(
        data.get("server_groups", []),
        [
            ("ID", "id", {"style": "cyan", "no_wrap": True}),
            ("Name", "name", {"style": "bold"}),
            ("Policy", lambda sg: ", ".join(sg.get("policies", []) or sg.get("policy", []))),
            ("Members", lambda sg: str(len(sg.get("members", [])))),
        ],
        title="Server Groups",
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
        empty_msg="No server groups found.",
    )


@server_group.command("show")
@click.argument("group_id")
@output_options
@click.pass_context
def server_group_show(ctx, group_id, output_format, columns, fit_width, max_width, noindent):
    """Show server group details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_nova(client)}/os-server-groups/{group_id}")
    sg = data.get("server_group", data)
    policies = sg.get("policies") or sg.get("policy") or []
    print_detail(
        [
            ("ID", sg.get("id", "")),
            ("Name", sg.get("name", "")),
            ("Policy", ", ".join(policies)),
            ("Members", ", ".join(sg.get("members", [])) or "—"),
            ("Project ID", sg.get("project_id", "")),
            ("User ID", sg.get("user_id", "")),
        ],
        output_format=output_format, columns=columns,
        fit_width=fit_width, max_width=max_width, noindent=noindent,
    )


@server_group.command("create")
@click.argument("name")
@click.option("--policy",
              type=click.Choice(["anti-affinity", "affinity",
                                 "soft-anti-affinity", "soft-affinity"],
                                case_sensitive=False),
              default="anti-affinity", show_default=True,
              help="Scheduling policy.")
@click.pass_context
def server_group_create(ctx, name, policy):
    """Create a server group.

    \b
    Policies:
      anti-affinity      — servers on different hosts (hard)
      affinity           — servers on same host (hard)
      soft-anti-affinity — prefer different hosts
      soft-affinity      — prefer same host
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.post(f"{_nova(client)}/os-server-groups",
                       json={"server_group": {"name": name, "policies": [policy]}})
    sg = data.get("server_group", data)
    console.print(f"[green]Server group '{sg.get('name')}' ({sg.get('id')}) created "
                  f"with policy '{policy}'.[/green]")


@server_group.command("delete")
@click.argument("group_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def server_group_delete(ctx, group_id, yes):
    """Delete a server group."""
    if not yes:
        click.confirm(f"Delete server group {group_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_nova(client)}/os-server-groups/{group_id}")
    console.print(f"[green]Server group {group_id} deleted.[/green]")
