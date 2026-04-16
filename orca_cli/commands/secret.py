"""``orca secret`` — manage secrets & containers (Barbican key-manager)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import output_options, print_list, print_detail, console
from orca_cli.core.validators import validate_id


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
@output_options
@click.pass_context
def secret_list(ctx: click.Context, limit: int | None, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List secrets."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_barbican(client)}/v1/secrets", params=params)

    def _uuid(s: dict) -> str:
        ref = s.get("secret_ref", "")
        return ref.rsplit("/", 1)[-1] if ref else ""

    print_list(
        data.get("secrets", []),
        [
            ("Name", lambda s: s.get("name", "") or "—", {"style": "bold"}),
            ("Secret Ref", _uuid, {"style": "cyan"}),
            ("Type", "secret_type"),
            ("Algorithm", lambda s: s.get("algorithm", "") or "—"),
            ("Status", "status", {"style": "green"}),
            ("Created", lambda s: str(s.get("created", ""))[:19]),
        ],
        title="Secrets",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No secrets found.",
    )


@secret.command("show")
@click.argument("secret_id", callback=validate_id)
@output_options
@click.pass_context
def secret_show(ctx: click.Context, secret_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show secret metadata."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/secrets/{secret_id}")

    fields = [(key, str(data.get(key, "") or "")) for key in
              ["name", "secret_ref", "secret_type", "status", "algorithm",
               "bit_length", "mode", "expiration", "content_types",
               "created", "updated"]]

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


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
      orca secret create my-password --payload "s3cret" --secret-type passphrase
      orca secret create my-key --algorithm AES --bit-length 256 --secret-type symmetric
    """
    client = ctx.find_object(OrcaContext).ensure_client()
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
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/secrets/{secret_id}")
    console.print(f"[green]Secret {secret_id} deleted.[/green]")


@secret.command("get-payload")
@click.argument("secret_id", callback=validate_id)
@click.pass_context
def secret_get_payload(ctx: click.Context, secret_id: str) -> None:
    """Retrieve secret payload."""
    client = ctx.find_object(OrcaContext).ensure_client()
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
@output_options
@click.pass_context
def container_list(ctx: click.Context, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List secret containers."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/containers")

    def _uuid(c: dict) -> str:
        ref = c.get("container_ref", "")
        return ref.rsplit("/", 1)[-1] if ref else ""

    print_list(
        data.get("containers", []),
        [
            ("Name", lambda c: c.get("name", "") or "—", {"style": "bold"}),
            ("Container Ref", _uuid, {"style": "cyan"}),
            ("Type", "type"),
            ("Secrets", lambda c: str(len(c.get("secret_refs", []))), {"justify": "right"}),
            ("Created", lambda c: str(c.get("created", ""))[:19]),
        ],
        title="Secret Containers",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No containers found.",
    )


@secret.command("container-show")
@click.argument("container_id", callback=validate_id)
@output_options
@click.pass_context
def container_show(ctx: click.Context, container_id: str, output_format: str, columns: tuple[str, ...], fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """Show secret container details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/containers/{container_id}")

    fields: list[tuple[str, str]] = [
        (key, str(data.get(key, "") or "")) for key in
        ["name", "container_ref", "type", "status", "created", "updated"]
    ]

    refs = data.get("secret_refs", [])
    if refs:
        fields.append(("", ""))
        fields.append(("── Secrets ──", ""))
        for r in refs:
            fields.append((f"  {r.get('name', '')}", r.get("secret_ref", "")))

    print_detail(fields, output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent, columns=columns)


@secret.command("container-delete")
@click.argument("container_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def container_delete(ctx: click.Context, container_id: str, yes: bool) -> None:
    """Delete a secret container."""
    if not yes:
        click.confirm(f"Delete container {container_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/containers/{container_id}")
    console.print(f"[green]Container {container_id} deleted.[/green]")


@secret.command("container-create")
@click.option("--name", default=None, help="Container name.")
@click.option("--type", "container_type",
              type=click.Choice(["generic", "rsa", "certificate"]),
              default="generic", show_default=True,
              help="Container type.")
@click.option("--secret", "secret_refs", multiple=True, metavar="NAME=SECRET_REF",
              help="Secret reference (repeatable): name=<secret-href>.")
@click.pass_context
def container_create(ctx: click.Context, name: str | None, container_type: str,
                     secret_refs: tuple[str, ...]) -> None:
    """Create a secret container.

    \b
    Example:
      orca secret container-create --name my-cert --type certificate \\
        --secret certificate=<secret-ref> \\
        --secret private_key=<secret-ref>
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    refs = []
    for ref in secret_refs:
        if "=" not in ref:
            raise click.UsageError(f"Invalid format '{ref}', expected NAME=SECRET_REF.")
        n, r = ref.split("=", 1)
        refs.append({"name": n, "secret_ref": r})
    body: dict = {"type": container_type, "secret_refs": refs}
    if name:
        body["name"] = name
    c = client.post(f"{_barbican(client)}/v1/containers",
                    json=body).get("container_ref", "?")
    console.print(f"[green]Container created: {c}[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Secret ACLs
# ══════════════════════════════════════════════════════════════════════════

@secret.command("acl-get")
@click.argument("secret_id", callback=validate_id)
@output_options
@click.pass_context
def secret_acl_get(ctx: click.Context, secret_id: str, output_format: str,
                   columns: tuple[str, ...], fit_width: bool,
                   max_width: int | None, noindent: bool) -> None:
    """Get the ACL for a secret."""
    client = ctx.find_object(OrcaContext).ensure_client()
    acl = client.get(f"{_barbican(client)}/v1/secrets/{secret_id}/acl")
    read_acl = acl.get("read", {})
    fields = [
        ("Project Access", str(read_acl.get("project-access", True))),
        ("Users", ", ".join(read_acl.get("users", [])) or "—"),
        ("Created", str(read_acl.get("created", ""))),
        ("Updated", str(read_acl.get("updated", ""))),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@secret.command("acl-set")
@click.argument("secret_id", callback=validate_id)
@click.option("--user", "users", multiple=True,
              help="User ID to grant read access to (repeatable).")
@click.option("--project-access/--no-project-access", default=True,
              help="Allow all project users read access.")
@click.pass_context
def secret_acl_set(ctx: click.Context, secret_id: str, users: tuple[str, ...],
                   project_access: bool) -> None:
    """Set the ACL on a secret."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"read": {"project-access": project_access, "users": list(users)}}
    client.put(f"{_barbican(client)}/v1/secrets/{secret_id}/acl", json=body)
    console.print(f"[green]ACL updated for secret {secret_id}.[/green]")


@secret.command("acl-delete")
@click.argument("secret_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def secret_acl_delete(ctx: click.Context, secret_id: str, yes: bool) -> None:
    """Delete the ACL on a secret (revert to project-wide access)."""
    if not yes:
        click.confirm(f"Delete ACL for secret {secret_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/secrets/{secret_id}/acl")
    console.print(f"[green]ACL deleted for secret {secret_id}.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Secret Orders (certificate / key / asymmetric)
# ══════════════════════════════════════════════════════════════════════════

@secret.command("order-list")
@output_options
@click.pass_context
def secret_order_list(ctx: click.Context, output_format: str, columns: tuple[str, ...],
                      fit_width: bool, max_width: int | None, noindent: bool) -> None:
    """List secret orders."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_barbican(client)}/v1/orders")
    orders = data.get("orders", [])
    print_list(
        orders,
        [
            ("Order Ref", "order_ref", {"style": "cyan"}),
            ("Type", "type", {"style": "bold"}),
            ("Status", "status", {"style": "green"}),
            ("Created", "created"),
        ],
        title="Secret Orders",
        output_format=output_format, fit_width=fit_width, max_width=max_width,
        noindent=noindent, columns=columns,
        empty_msg="No orders found.",
    )


@secret.command("order-show")
@click.argument("order_id", callback=validate_id)
@output_options
@click.pass_context
def secret_order_show(ctx: click.Context, order_id: str, output_format: str,
                      columns: tuple[str, ...], fit_width: bool,
                      max_width: int | None, noindent: bool) -> None:
    """Show an order's details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    o = client.get(f"{_barbican(client)}/v1/orders/{order_id}")
    fields = [
        ("Order Ref", str(o.get("order_ref", ""))),
        ("Type", str(o.get("type", ""))),
        ("Status", str(o.get("status", ""))),
        ("Secret Ref", str(o.get("secret_ref", "") or "—")),
        ("Created", str(o.get("created", ""))),
        ("Updated", str(o.get("updated", ""))),
        ("Error Reason", str(o.get("error_reason", "") or "—")),
    ]
    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@secret.command("order-create")
@click.option("--type", "order_type",
              type=click.Choice(["key", "asymmetric", "certificate"]),
              required=True, help="Order type.")
@click.option("--name", default=None, help="Secret name for the resulting secret.")
@click.option("--algorithm", default=None, help="Key algorithm (e.g. aes, rsa).")
@click.option("--bit-length", type=int, default=None, help="Key bit length.")
@click.option("--mode", default=None, help="Encryption mode (e.g. cbc).")
@click.pass_context
def secret_order_create(ctx: click.Context, order_type: str, name: str | None,
                        algorithm: str | None, bit_length: int | None,
                        mode: str | None) -> None:
    """Create a secret order (async key/certificate generation).

    \b
    Examples:
      orca secret order-create --type key --algorithm aes --bit-length 256
      orca secret order-create --type asymmetric --algorithm rsa --bit-length 2048
    """
    client = ctx.find_object(OrcaContext).ensure_client()
    meta: dict = {}
    if name:
        meta["name"] = name
    if algorithm:
        meta["algorithm"] = algorithm
    if bit_length:
        meta["bit_length"] = bit_length
    if mode:
        meta["mode"] = mode
    body: dict = {"type": order_type, "meta": meta}
    o = client.post(f"{_barbican(client)}/v1/orders", json=body)
    console.print(f"[green]Order created: {o.get('order_ref', '?')}[/green]")


@secret.command("order-delete")
@click.argument("order_id", callback=validate_id)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def secret_order_delete(ctx: click.Context, order_id: str, yes: bool) -> None:
    """Delete a secret order."""
    if not yes:
        click.confirm(f"Delete order {order_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_barbican(client)}/v1/orders/{order_id}")
    console.print(f"[green]Order {order_id} deleted.[/green]")
