"""Generic async resource poller for --wait flags.

Usage example::

    from orca_cli.core.waiter import wait_for_resource

    wait_for_resource(
        client,
        url=f"{client.compute_url}/servers/{srv_id}",
        resource_key="server",
        target_status="ACTIVE",
        label=f"Server {name}",
    )
"""

from __future__ import annotations

import time

import click

from orca_cli.core.output import console


def wait_for_resource(
    client,
    url: str,
    resource_key: str,
    target_status: str,
    *,
    label: str = "",
    error_status: str = "ERROR",
    timeout: int = 300,
    interval: int = 5,
    delete_mode: bool = False,
) -> None:
    """Poll a resource until it reaches *target_status* (or disappears in delete mode).

    Args:
        client:        OrcaClient instance.
        url:           Full resource URL to GET repeatedly.
        resource_key:  Top-level JSON key of the resource (e.g. ``"server"``).
        target_status: Status string to wait for (case-insensitive).
        label:         Human-readable label shown in the progress spinner.
        error_status:  Status that means the operation failed (default ``"ERROR"``).
        timeout:       Maximum seconds to wait before raising.
        interval:      Seconds between polls.
        delete_mode:   When True, a 404 response is treated as success.
    """
    from orca_cli.core.exceptions import APIError

    target = target_status.upper()
    display = label or url
    start = time.monotonic()

    with console.status(f"[bold cyan]Waiting for {display} → {target}…[/bold cyan]") as spinner:
        while True:
            elapsed = time.monotonic() - start

            if elapsed >= timeout:
                raise click.ClickException(
                    f"Timeout after {timeout}s — {display} never reached {target}."
                )

            try:
                data = client.get(url)
            except APIError as exc:
                if delete_mode and getattr(exc, "status_code", None) == 404:
                    console.print(f"[green]{display} deleted ({elapsed:.0f}s).[/green]")
                    return
                raise

            resource = data.get(resource_key, data)
            current = resource.get("status", "UNKNOWN").upper()

            if current == target:
                console.print(f"[green]{display} is {target} ({elapsed:.0f}s).[/green]")
                return

            if error_status and current == error_status.upper():
                fault = (
                    resource.get("fault", {}).get("message", "")
                    or resource.get("message", "")
                )
                msg = f"{display} entered {error_status} state."
                if fault:
                    msg += f" Details: {fault}"
                raise click.ClickException(msg)

            spinner.update(
                f"[bold cyan]Waiting for {display} → {target} "
                f"(current: {current}, {elapsed:.0f}s)…[/bold cyan]"
            )
            time.sleep(interval)
