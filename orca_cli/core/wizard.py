"""Interactive wizard helpers — step-by-step resource selection via Rich + click.prompt."""

from __future__ import annotations

import click
from rich.table import Table

from orca_cli.core.output import console


# ── Generic selector ──────────────────────────────────────────────────────

def wizard_select(
    items: list,
    label: str,
    headers: list[str],
    row_fn,  # callable(item) -> tuple[str, ...]
    *,
    allow_none: bool = False,
    none_label: str = "None / skip",
) -> int | None:
    """Display a numbered Rich table and prompt for a selection.

    Returns the 0-based index into *items*, or None if *allow_none* and the
    user chose 0.  Raises :class:`click.Abort` when the list is empty.
    """
    if not items:
        console.print(f"[yellow]No {label.lower()} available.[/yellow]")
        raise click.Abort()

    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("#", width=4, justify="right", style="dim")
    for h in headers:
        table.add_column(h)

    if allow_none:
        table.add_row("0", f"[dim]{none_label}[/dim]", *["—"] * (len(headers) - 1))

    for i, item in enumerate(items, 1):
        table.add_row(str(i), *row_fn(item))

    console.print(table)

    lo = 0 if allow_none else 1
    choice = click.prompt(
        f"  Select {label}",
        type=click.IntRange(lo, len(items)),
        prompt_suffix=" > ",
    )
    return None if (allow_none and choice == 0) else choice - 1


# ── Resource selectors ─────────────────────────────────────────────────────

def select_image(client) -> tuple[str, str]:
    """Interactive image selection. Returns ``(id, name)``."""
    images = client.get(
        f"{client.image_url}/v2/images",
        params={"status": "active", "limit": 20,
                "sort_key": "updated_at", "sort_dir": "desc"},
    ).get("images", [])

    console.print("\n[bold cyan]Available Images[/bold cyan]")
    idx = wizard_select(
        images,
        "Image",
        ["Name", "OS", "Size"],
        lambda img: (
            img.get("name", "—"),
            img.get("os_distro", img.get("os_type", "—")),
            _fmt_bytes(img.get("size") or 0),
        ),
    )
    if idx is None:
        raise click.Abort()
    img = images[idx]
    return img["id"], img.get("name", img["id"])


def select_flavor(client) -> tuple[str, str, int, int]:
    """Interactive flavor selection. Returns ``(id, name, vcpus, ram_mb)``."""
    flavors = sorted(
        client.get(f"{client.compute_url}/flavors/detail").get("flavors", []),
        key=lambda f: (f.get("ram", 0), f.get("vcpus", 0)),
    )

    console.print("\n[bold cyan]Available Flavors[/bold cyan]")
    idx = wizard_select(
        flavors,
        "Flavor",
        ["Name", "vCPUs", "RAM", "Disk"],
        lambda f: (
            f.get("name", "—"),
            str(f.get("vcpus", "—")),
            _fmt_ram(f.get("ram", 0)),
            f"{f.get('disk', 0)} GB",
        ),
    )
    if idx is None:
        raise click.Abort()
    fl = flavors[idx]
    return fl["id"], fl.get("name", fl["id"]), fl.get("vcpus", 0), fl.get("ram", 0)


def select_network(client) -> tuple[str, str] | None:
    """Interactive network selection (optional). Returns ``(id, name)`` or None."""
    networks = client.get(f"{client.network_url}/v2.0/networks").get("networks", [])

    console.print("\n[bold cyan]Available Networks[/bold cyan]")
    idx = wizard_select(
        networks,
        "Network",
        ["Name", "Status", "Shared"],
        lambda n: (
            n.get("name", "—"),
            n.get("status", "—"),
            "Yes" if n.get("shared") else "No",
        ),
        allow_none=True,
        none_label="No network attachment",
    )
    if idx is None:
        return None
    net = networks[idx]
    return net["id"], net.get("name", net["id"])


def select_keypair(client) -> str | None:
    """Interactive keypair selection (optional). Returns name or None."""
    raw = client.get(f"{client.compute_url}/os-keypairs").get("keypairs", [])
    kps = [k["keypair"] for k in raw]

    console.print("\n[bold cyan]Available Keypairs[/bold cyan]")
    idx = wizard_select(
        kps,
        "Keypair",
        ["Name", "Type", "Fingerprint"],
        lambda k: (
            k.get("name", "—"),
            k.get("type", "ssh"),
            (k.get("fingerprint", "") or "")[:24] + "…",
        ),
        allow_none=True,
        none_label="No SSH key (password only)",
    )
    return None if idx is None else kps[idx]["name"]


def select_security_groups(client) -> list[str]:
    """Interactive multi-select for security groups. Returns list of names."""
    sgs = client.get(f"{client.network_url}/v2.0/security-groups").get("security_groups", [])

    console.print("\n[bold cyan]Security Groups[/bold cyan]")
    console.print("[dim]Enter numbers separated by commas (e.g. 1,3). Leave blank to skip.[/dim]")

    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("#", width=4, justify="right", style="dim")
    table.add_column("Name")
    table.add_column("Description")
    for i, sg in enumerate(sgs, 1):
        table.add_row(str(i), sg.get("name", "—"), (sg.get("description", "") or "")[:50])
    console.print(table)

    raw = click.prompt("  Select Security Groups", default="", prompt_suffix=" > ")
    if not raw.strip():
        return []

    selected: list[str] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(sgs):
                selected.append(sgs[idx]["name"])
        except ValueError:
            pass
    return selected


def select_volume_type(client) -> str | None:
    """Interactive volume type selection (optional). Returns type name or None."""
    types = client.get(f"{client.volume_url}/types").get("volume_types", [])

    console.print("\n[bold cyan]Volume Types[/bold cyan]")
    idx = wizard_select(
        types,
        "Volume Type",
        ["Name", "Description"],
        lambda t: (
            t.get("name", "—"),
            (t.get("description", "") or "")[:50],
        ),
        allow_none=True,
        none_label="Default type",
    )
    return None if idx is None else types[idx]["name"]


# ── Quota preview ─────────────────────────────────────────────────────────

def quota_preview(client, vcpus: int, ram_mb: int) -> None:
    """Print a before/after quota summary for a server create operation."""
    try:
        q = (
            client.get(f"{client.compute_url}/limits")
            .get("limits", {})
            .get("absolute", {})
        )
        inst_used = q.get("totalInstancesUsed", 0)
        inst_max  = q.get("maxTotalInstances", -1)
        cpu_used  = q.get("totalCoresUsed", 0)
        cpu_max   = q.get("maxTotalCores", -1)
        ram_used  = q.get("totalRAMUsed", 0)
        ram_max   = q.get("maxTotalRAMSize", -1)

        console.print("\n[bold]Quota Impact[/bold]")
        _quota_line("Instances", inst_used, inst_used + 1, inst_max)
        _quota_line("vCPUs",     cpu_used,  cpu_used + vcpus, cpu_max)
        _quota_line(
            "RAM",
            ram_used // 1024,
            (ram_used + ram_mb) // 1024,
            ram_max // 1024 if ram_max > 0 else -1,
            unit="GB",
        )
    except Exception:
        pass  # best-effort — don't block the wizard on quota errors


def _quota_line(label: str, before: int, after: int, limit: int, unit: str = "") -> None:
    u = f" {unit}" if unit else ""
    if limit <= 0:
        console.print(f"  {label}: {before}{u} → {after}{u} [dim](no limit)[/dim]")
        return
    pct = int(after / limit * 100)
    color = "red" if pct >= 90 else "yellow" if pct >= 70 else "green"
    console.print(f"  {label}: {before}{u} → [{color}]{after}/{limit}{u} ({pct}%)[/{color}]")


# ── CLI-equivalent builder ─────────────────────────────────────────────────

def build_server_command(
    name: str,
    image_id: str,
    flavor_id: str,
    disk_size: int,
    network_id: str | None,
    key_name: str | None,
    security_groups: list[str],
) -> str:
    """Return the equivalent ``orca server create`` CLI command string."""
    parts = [
        "orca server create",
        f"  --name {name}",
        f"  --image {image_id}",
        f"  --flavor {flavor_id}",
        f"  --disk-size {disk_size}",
    ]
    if network_id:
        parts.append(f"  --network {network_id}")
    if key_name:
        parts.append(f"  --key-name {key_name}")
    for sg in security_groups:
        parts.append(f"  --security-group {sg}")
    return " \\\n".join(parts)


# ── CIDR selector (for doctor --fix) ─────────────────────────────────────

def select_cidr() -> str:
    """Prompt the user for a CIDR to apply to a security group rule."""
    console.print("\n[bold cyan]Security Rule Scope[/bold cyan]")
    table = Table(show_header=False, show_lines=False, box=None)
    table.add_column("#", width=4, justify="right", style="dim")
    table.add_column("Option")
    table.add_row("1", "0.0.0.0/0  — open to everyone [dim](less secure)[/dim]")
    table.add_row("2", "Custom CIDR or single IP  [dim](e.g. 203.0.113.5/32)[/dim]")
    console.print(table)

    choice = click.prompt("  Select", type=click.IntRange(1, 2), prompt_suffix=" > ")
    if choice == 1:
        return "0.0.0.0/0"
    return click.prompt("  Enter CIDR", prompt_suffix=" > ")


# ── Formatting helpers ────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.1f} GB"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    return f"{n} B"


def _fmt_ram(mb: int) -> str:
    if mb >= 1024:
        return f"{mb // 1024} GB"
    return f"{mb} MB"
