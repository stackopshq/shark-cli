"""``shark secret`` — manage secrets & containers (Barbican key-manager)."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from shark_cli.core.context import SharkContext
from shark_cli.core.validators import validate_id

console = Console()


def _barbican(client) -> str:
    return client.key_manager_url


# ══════════════════════════════════════════════════════════════════════════
#  Top-level group
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def secret(ctx: click.Context) -> None:
    """Manage secrets & containers (Barbican key-manager)."""
    pass


# ══════════════════════════════════════════════════════════════════════════
#  Secrets
# ══════════════════════════════════════════════════════════════════════════

@secret.command("list")
@click.option("--limit", type=int, default=None, help="Max results.")
@click.pass_context
def secret_list(ctx: click.Context, limit: int | None) -> None:
    """List secrets."""
    client = ctx.find_object(SharkContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_barbican(client)}/v1/secrets", params=params)
    secrets = data.get("secrets", [])
    if not secrets:
        console.print("[yellow]No secrets found.[/yellow]")
        return

    table = Table(title="Secrets", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Secret Ref", style="cyan")
    table.add_column("Type")
    table.add_column("Algorithm")
    table.add_column("Status", style="green")
    table.add_column("Created")

    for s in secrets:
        ref = s.get("secret_ref", "")
        uuid = ref.rsplit("/", 1)[-1] if ref else ""
        table.add_row(
            s.get("name", "") or "—",
            uuid,
            s.get("secret_type", ""),
            s.get("algorithm", "") or "—",
            s.get("status", ""),
            str(s.get("created", ""))[:19],
        )
    console.print(table)


@secret.command("show")
@click.argument("secret_id", callback=validate_id)
@click.pass_context
def secret_show(ctx: click.Context, secret_id: str) -> None:
    """Show secret metadata."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/secrets/{secret_id}")

    table = Table(title=f"Secret {data.get('name') or secret_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["name", "secret_ref", "secret_type", "status", "algorithm",
                "bit_length", "mode", "expiration", "content_types",
                "created", "updated"]:
        table.add_row(key, str(data.get(key, "") or ""))
    console.print(table)


@secret.command("create")
@click.argument("name")
@click.option("--payload", default=None, help="Secret payload (inline).")
@click.option("--payload-content-type", "content_type", default="text/plain",
              show_default=True, help="MIME type of payload.")
@click.option("--secret-type", "secret_type", default="opaque",
              type=click.Choice(["symmetric", "public", "private", "passphrase",
                                 "certificate", "opaque"]),
              show_default=True)
@click.option("--algorithm", default=None, help="Algorithm (e.g. AES, RSA).")
@click.option("--bit-length", type=int, default=None, help="Bit length.")
@click.option("--expiration", default=None, help="Expiration datetime (ISO 8601).")
@click.pass_context
def secret_create(ctx: click.Context, name: str, payload: str | None,
                  content_type: str, secret_type: str,
                  algorithm: str | None, bit_length: int | None,
                  expiration: str | None) -> None:
    """Create a secret.

    \b
    Examples:
      shark secret create my-password --payload "s3cret" --secret-type passphrase
      shark secret create my-key --algorithm AES --bit-length 256 --secret-type symmetric
    """
    client = ctx.find_object(SharkContext).ensure_client()
    body: dict = {"name": name, "secret_type": secret_type}
    if payload:
        body["payload"] = payload
        body["payload_content_type"] = content_type
    if algorithm:
        body["algorithm"] = algorithm
    if bit_length:
        body["bit_length"] = bit_length
    if expiration:
        body["expiration"] = expiration

    data = client.post(f"{_barbican(client)}/v1/secrets", json=body)
    ref = data.get("secret_ref", "") if data else ""
    uuid = ref.rsplit("/", 1)[-1] if ref else ""
    console.print(f"[green]Secret '{name}' created ({uuid}).[/green]")


@secret.command("delete")
@click.argument("secret_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def secret_delete(ctx: click.Context, secret_id: str, yes: bool) -> None:
    """Delete a secret."""
    if not yes:
        click.confirm(f"Delete secret {secret_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/secrets/{secret_id}")
    console.print(f"[green]Secret {secret_id} deleted.[/green]")


@secret.command("get-payload")
@click.argument("secret_id", callback=validate_id)
@click.pass_context
def secret_get_payload(ctx: click.Context, secret_id: str) -> None:
    """Retrieve secret payload."""
    client = ctx.find_object(SharkContext).ensure_client()
    url = f"{_barbican(client)}/v1/secrets/{secret_id}/payload"
    headers = {"X-Auth-Token": client._token or "", "Accept": "text/plain"}
    resp = client._http.get(url, headers=headers)
    if resp.status_code == 200:
        console.print(resp.text)
    else:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")


# ══════════════════════════════════════════════════════════════════════════
#  Containers
# ══════════════════════════════════════════════════════════════════════════

@secret.command("container-list")
@click.pass_context
def container_list(ctx: click.Context) -> None:
    """List secret containers."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/containers")
    containers = data.get("containers", [])
    if not containers:
        console.print("[yellow]No containers found.[/yellow]")
        return

    table = Table(title="Secret Containers", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Container Ref", style="cyan")
    table.add_column("Type")
    table.add_column("Secrets", justify="right")
    table.add_column("Created")

    for c in containers:
        ref = c.get("container_ref", "")
        uuid = ref.rsplit("/", 1)[-1] if ref else ""
        table.add_row(
            c.get("name", "") or "—",
            uuid,
            c.get("type", ""),
            str(len(c.get("secret_refs", []))),
            str(c.get("created", ""))[:19],
        )
    console.print(table)


@secret.command("container-show")
@click.argument("container_id", callback=validate_id)
@click.pass_context
def container_show(ctx: click.Context, container_id: str) -> None:
    """Show secret container details."""
    client = ctx.find_object(SharkContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/containers/{container_id}")

    table = Table(title=f"Container {data.get('name') or container_id}", show_lines=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    for key in ["name", "container_ref", "type", "status", "created", "updated"]:
        table.add_row(key, str(data.get(key, "") or ""))

    refs = data.get("secret_refs", [])
    if refs:
        table.add_row("", "")
        table.add_row("[bold]── Secrets ──[/bold]", "")
        for r in refs:
            table.add_row(f"  {r.get('name', '')}", r.get("secret_ref", ""))

    console.print(table)


@secret.command("container-delete")
@click.argument("container_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def container_delete(ctx: click.Context, container_id: str, yes: bool) -> None:
    """Delete a secret container."""
    if not yes:
        click.confirm(f"Delete container {container_id}?", abort=True)
    client = ctx.find_object(SharkContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/containers/{container_id}")
    console.print(f"[green]Container {container_id} deleted.[/green]")
