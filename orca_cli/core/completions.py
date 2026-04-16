"""Shell completion helpers backed by the local resource cache.

Each ``complete_*`` function follows the Click ``shell_complete`` callback
signature: ``(ctx, param, incomplete) -> list[CompletionItem]``.

Items are fetched from the API on the first call within a 30-second window
and served from a local JSON cache thereafter, making tab completion nearly
instantaneous after the first use.
"""

from __future__ import annotations

import click
from click.shell_completion import CompletionItem


# ── internal helpers ──────────────────────────────────────────────────────

def _build_client(ctx: click.Context):
    """Build an OrcaClient for completion context (returns (client, profile))."""
    try:
        from orca_cli.core.config import load_config, config_is_complete
        from orca_cli.core.client import OrcaClient

        # Walk context chain for --profile value
        profile = None
        c: click.Context | None = ctx
        while c:
            if "profile" in getattr(c, "params", {}) and c.params["profile"]:
                profile = c.params["profile"]
                break
            c = c.parent

        config = load_config(profile_name=profile)
        if not config_is_complete(config):
            return None, profile
        return OrcaClient(config), profile
    except Exception:
        return None, None


def _complete(
    ctx: click.Context,
    incomplete: str,
    resource: str,
    fetch_fn,
    item_fn,
) -> list[CompletionItem]:
    """Generic completion: load cache or fetch, then filter by incomplete."""
    from orca_cli.core import cache

    items = cache.load(None, resource)
    if items is None:
        client, profile = _build_client(ctx)
        if client:
            try:
                items = fetch_fn(client)
                cache.save(profile, resource, items)
            except Exception:
                items = []
            finally:
                try:
                    client.close()
                except Exception:
                    pass
        else:
            items = []

    low = incomplete.lower()
    return [item_fn(i) for i in items if _matches(i, low)]


def _matches(item: dict, low: str) -> bool:
    return low in item.get("id", "").lower() or low in item.get("name", "").lower()


# ── public completion functions ───────────────────────────────────────────

def complete_servers(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete server IDs/names."""
    return _complete(
        ctx, incomplete, "servers",
        lambda c: [{"id": s["id"], "name": s.get("name", "")}
                   for s in c.get(f"{c.compute_url}/servers/detail", params={"limit": 500}).get("servers", [])],
        lambda i: CompletionItem(i["id"], help=i["name"]),
    )


def complete_volumes(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete volume IDs/names."""
    return _complete(
        ctx, incomplete, "volumes",
        lambda c: [{"id": v["id"], "name": v.get("name", "")}
                   for v in c.get(f"{c.volume_url}/volumes/detail", params={"limit": 500}).get("volumes", [])],
        lambda i: CompletionItem(i["id"], help=i["name"]),
    )


def complete_images(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete image IDs/names."""
    return _complete(
        ctx, incomplete, "images",
        lambda c: [{"id": img["id"], "name": img.get("name", "")}
                   for img in c.get(f"{c.image_url}/v2/images", params={"limit": 500}).get("images", [])],
        lambda i: CompletionItem(i["id"], help=i["name"]),
    )


def complete_networks(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete network IDs/names."""
    return _complete(
        ctx, incomplete, "networks",
        lambda c: [{"id": n["id"], "name": n.get("name", "")}
                   for n in c.get(f"{c.network_url}/v2.0/networks").get("networks", [])],
        lambda i: CompletionItem(i["id"], help=i["name"]),
    )


def complete_flavors(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete flavor IDs/names."""
    return _complete(
        ctx, incomplete, "flavors",
        lambda c: [{"id": f["id"], "name": f.get("name", "")}
                   for f in c.get(f"{c.compute_url}/flavors/detail").get("flavors", [])],
        lambda i: CompletionItem(i["id"], help=i["name"]),
    )


def complete_keypairs(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete keypair names."""
    def _fetch(c):
        return [{"id": k["keypair"]["name"], "name": ""}
                for k in c.get(f"{c.compute_url}/os-keypairs").get("keypairs", [])]

    return _complete(
        ctx, incomplete, "keypairs",
        _fetch,
        lambda i: CompletionItem(i["id"]),
    )


def complete_security_groups(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    """Complete security group names."""
    return _complete(
        ctx, incomplete, "security_groups",
        lambda c: [{"id": sg["id"], "name": sg.get("name", "")}
                   for sg in c.get(f"{c.network_url}/v2.0/security-groups").get("security_groups", [])],
        lambda i: CompletionItem(i["name"] or i["id"], help=i["id"]),
    )
