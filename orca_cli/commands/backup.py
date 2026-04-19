"""``orca backup`` — manage backups, jobs, sessions & clients (Freezer)."""

from __future__ import annotations

import click

from orca_cli.core.context import OrcaContext
from orca_cli.core.output import console, output_options, print_detail, print_list


def _freezer(client) -> str:
    return client.backup_url


# ══════════════════════════════════════════════════════════════════════════
#  Top-level group
# ══════════════════════════════════════════════════════════════════════════

@click.group()
@click.pass_context
def backup(ctx: click.Context) -> None:
    """Manage Freezer backups, jobs, sessions & clients.

    For Cinder volume backups see ``orca volume backup-list`` etc.
    """
    pass


# ══════════════════════════════════════════════════════════════════════════
#  Backups
# ══════════════════════════════════════════════════════════════════════════

@backup.command("list")
@click.option("--limit", type=int, default=None, help="Max results.")
@click.option("--offset", type=int, default=None, help="Offset for pagination.")
@output_options
@click.pass_context
def backup_list(ctx: click.Context, limit: int | None, offset: int | None,
                output_format: str, columns: tuple[str, ...], fit_width: bool,
                max_width: int | None, noindent: bool) -> None:
    """List backups."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    data = client.get(f"{_freezer(client)}/v2/backups", params=params)

    backups = data.get("backups", []) if isinstance(data, dict) else data

    print_list(
        backups,
        [
            ("Backup ID", "backup_id", {"style": "cyan", "no_wrap": True}),
            ("Name", lambda b: b.get("backup_name", "") or b.get("backup_metadata", {}).get("backup_name", "") or "—", {"style": "bold"}),
            ("Container", lambda b: b.get("container", "") or "—"),
            ("Level", lambda b: str(b.get("curr_backup_level", 0)), {"justify": "right"}),
            ("Status", lambda b: b.get("status", "") or "—", {"style": "green"}),
            ("Timestamp", lambda b: str(b.get("time_stamp", ""))[:19]),
        ],
        title="Backups",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No backups found.",
    )


@backup.command("show")
@click.argument("backup_id")
@output_options
@click.pass_context
def backup_show(ctx: click.Context, backup_id: str, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """Show backup details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_freezer(client)}/v2/backups/{backup_id}")

    fields = [(key, str(data.get(key, "") or "")) for key in
              ["backup_id", "backup_name", "container", "status",
               "curr_backup_level", "storage", "mode", "engine_name",
               "time_stamp", "path_to_backup", "hostname",
               "os_auth_version", "project_id"]]

    # Include backup_metadata if present
    meta = data.get("backup_metadata", {})
    if meta:
        for k, v in meta.items():
            if k not in ("backup_id", "backup_name"):
                fields.append((f"meta:{k}", str(v)))

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@backup.command("delete")
@click.argument("backup_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def backup_delete(ctx: click.Context, backup_id: str, yes: bool) -> None:
    """Delete a backup."""
    if not yes:
        click.confirm(f"Delete backup {backup_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/backups/{backup_id}")
    console.print(f"[green]Backup {backup_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Jobs
# ══════════════════════════════════════════════════════════════════════════

@backup.command("job-list")
@click.option("--limit", type=int, default=None, help="Max results.")
@output_options
@click.pass_context
def job_list(ctx: click.Context, limit: int | None, output_format: str,
             columns: tuple[str, ...], fit_width: bool, max_width: int | None,
             noindent: bool) -> None:
    """List backup jobs."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_freezer(client)}/v2/jobs", params=params)

    jobs = data.get("jobs", []) if isinstance(data, dict) else data

    print_list(
        jobs,
        [
            ("Job ID", "job_id", {"style": "cyan", "no_wrap": True}),
            ("Description", lambda j: j.get("description", "") or "—", {"style": "bold"}),
            ("Client ID", lambda j: j.get("client_id", "")[:12] if j.get("client_id") else "—"),
            ("Status", lambda j: j.get("job_schedule", {}).get("status", "") or "—", {"style": "green"}),
            ("Event", lambda j: j.get("job_schedule", {}).get("event", "") or "—"),
            ("Actions", lambda j: str(len(j.get("job_actions", []))), {"justify": "right"}),
        ],
        title="Backup Jobs",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No jobs found.",
    )


@backup.command("job-show")
@click.argument("job_id")
@output_options
@click.pass_context
def job_show(ctx: click.Context, job_id: str, output_format: str,
             columns: tuple[str, ...], fit_width: bool, max_width: int | None,
             noindent: bool) -> None:
    """Show backup job details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_freezer(client)}/v2/jobs/{job_id}")

    sched = data.get("job_schedule", {})
    fields = [
        ("Job ID", data.get("job_id", "")),
        ("Description", data.get("description", "")),
        ("Client ID", data.get("client_id", "")),
        ("User ID", data.get("user_id", "")),
        ("Project ID", data.get("project_id", "")),
        ("Session ID", data.get("session_id", "") or "—"),
        ("Schedule Status", sched.get("status", "")),
        ("Schedule Event", sched.get("event", "")),
        ("Schedule Time", sched.get("time", "") or "—"),
    ]

    actions = data.get("job_actions", [])
    if actions:
        fields.append(("", ""))
        fields.append(("── Actions ──", ""))
        for i, a in enumerate(actions):
            fa = a.get("freezer_action", {})
            fields.append((f"  Action {i + 1}", fa.get("action", "")))
            fields.append(("  Path", fa.get("path_to_backup", "") or fa.get("restore_abs_path", "") or "—"))
            fields.append(("  Container", fa.get("container", "") or "—"))
            fields.append(("  Storage", fa.get("storage", "") or "—"))
            fields.append(("  Mode", fa.get("mode", "") or "—"))

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@backup.command("job-create")
@click.option("--description", default="", help="Job description.")
@click.option("--client-id", required=True, help="Freezer client ID.")
@click.option("--action", "action_type", type=click.Choice(["backup", "restore", "admin"]),
              default="backup", show_default=True, help="Action type.")
@click.option("--path", "path_to_backup", required=True, help="Path to back up or restore.")
@click.option("--container", default=None, help="Swift container name for storage.")
@click.option("--storage", type=click.Choice(["swift", "local", "ssh", "s3"]),
              default="swift", show_default=True, help="Storage backend.")
@click.option("--mode", type=click.Choice(["fs", "mysql", "mongo", "mssql", "cinder", "nova"]),
              default="fs", show_default=True, help="Backup mode.")
@click.option("--schedule-interval", default=None, help="Schedule interval (e.g. '24 hours', '7 days').")
@click.pass_context
def job_create(ctx: click.Context, description: str, client_id: str,
               action_type: str, path_to_backup: str, container: str | None,
               storage: str, mode: str, schedule_interval: str | None) -> None:
    """Create a backup job.

    \b
    Examples:
      orca backup job-create --client-id <id> --path /var/data --container my-backups
      orca backup job-create --client-id <id> --path /var/lib/mysql --mode mysql --storage swift
      orca backup job-create --client-id <id> --action restore --path /var/data --container my-backups
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    freezer_action: dict = {
        "action": action_type,
        "mode": mode,
        "storage": storage,
    }
    if action_type == "backup":
        freezer_action["path_to_backup"] = path_to_backup
    else:
        freezer_action["restore_abs_path"] = path_to_backup

    if container:
        freezer_action["container"] = container

    body: dict = {
        "description": description,
        "client_id": client_id,
        "job_actions": [{"freezer_action": freezer_action}],
        "job_schedule": {},
    }

    if schedule_interval:
        body["job_schedule"]["schedule_interval"] = schedule_interval

    data = client.post(f"{_freezer(client)}/v2/jobs", json=body)
    job_id = data.get("job_id", "") if data else ""
    console.print(f"[green]Job created ({job_id}).[/green]")


@backup.command("job-start")
@click.argument("job_id")
@click.pass_context
def job_start(ctx: click.Context, job_id: str) -> None:
    """Start (trigger) a backup job."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_freezer(client)}/v2/jobs/{job_id}/event", json={"event": "start"})
    console.print(f"[green]Job {job_id} started.[/green]")


@backup.command("job-stop")
@click.argument("job_id")
@click.pass_context
def job_stop(ctx: click.Context, job_id: str) -> None:
    """Stop a running backup job."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_freezer(client)}/v2/jobs/{job_id}/event", json={"event": "stop"})
    console.print(f"[green]Job {job_id} stopped.[/green]")


@backup.command("job-delete")
@click.argument("job_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def job_delete(ctx: click.Context, job_id: str, yes: bool) -> None:
    """Delete a backup job."""
    if not yes:
        click.confirm(f"Delete job {job_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/jobs/{job_id}")
    console.print(f"[green]Job {job_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Sessions
# ══════════════════════════════════════════════════════════════════════════

@backup.command("session-list")
@click.option("--limit", type=int, default=None, help="Max results.")
@output_options
@click.pass_context
def session_list(ctx: click.Context, limit: int | None, output_format: str,
                 columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                 noindent: bool) -> None:
    """List backup sessions."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_freezer(client)}/v2/sessions", params=params)

    sessions = data.get("sessions", []) if isinstance(data, dict) else data

    print_list(
        sessions,
        [
            ("Session ID", "session_id", {"style": "cyan", "no_wrap": True}),
            ("Description", lambda s: s.get("description", "") or "—", {"style": "bold"}),
            ("Status", lambda s: s.get("status", "") or "—", {"style": "green"}),
            ("Jobs", lambda s: str(len(s.get("jobs", {}))), {"justify": "right"}),
            ("Time Start", lambda s: str(s.get("time_start", "") or "—")[:19]),
            ("Time End", lambda s: str(s.get("time_end", "") or "—")[:19]),
        ],
        title="Backup Sessions",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No sessions found.",
    )


@backup.command("session-show")
@click.argument("session_id")
@output_options
@click.pass_context
def session_show(ctx: click.Context, session_id: str, output_format: str,
                 columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                 noindent: bool) -> None:
    """Show backup session details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_freezer(client)}/v2/sessions/{session_id}")

    fields = [(key, str(data.get(key, "") or "")) for key in
              ["session_id", "description", "status", "user_id", "project_id",
               "time_start", "time_end", "schedule"]]

    jobs = data.get("jobs", {})
    if jobs:
        fields.append(("", ""))
        fields.append(("── Jobs ──", ""))
        for job_id, job_info in jobs.items():
            status = job_info.get("status", "") if isinstance(job_info, dict) else str(job_info)
            fields.append((f"  {job_id}", status))

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@backup.command("session-create")
@click.option("--description", default="", help="Session description.")
@click.option("--schedule-interval", default=None, help="Schedule interval (e.g. '24 hours').")
@click.pass_context
def session_create(ctx: click.Context, description: str, schedule_interval: str | None) -> None:
    """Create a backup session."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body: dict = {"description": description}
    if schedule_interval:
        body["schedule"] = {"schedule_interval": schedule_interval}

    data = client.post(f"{_freezer(client)}/v2/sessions", json=body)
    session_id = data.get("session_id", "") if data else ""
    console.print(f"[green]Session created ({session_id}).[/green]")


@backup.command("session-add-job")
@click.argument("session_id")
@click.argument("job_id")
@click.pass_context
def session_add_job(ctx: click.Context, session_id: str, job_id: str) -> None:
    """Add a job to a session."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.put(f"{_freezer(client)}/v2/sessions/{session_id}/jobs/{job_id}")
    console.print(f"[green]Job {job_id} added to session {session_id}.[/green]")


@backup.command("session-remove-job")
@click.argument("session_id")
@click.argument("job_id")
@click.pass_context
def session_remove_job(ctx: click.Context, session_id: str, job_id: str) -> None:
    """Remove a job from a session."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/sessions/{session_id}/jobs/{job_id}")
    console.print(f"[green]Job {job_id} removed from session {session_id}.[/green]")


@backup.command("session-start")
@click.argument("session_id")
@click.pass_context
def session_start(ctx: click.Context, session_id: str) -> None:
    """Start a backup session (triggers all its jobs)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    client.post(f"{_freezer(client)}/v2/sessions/{session_id}/action", json={"start": None})
    console.print(f"[green]Session {session_id} started.[/green]")


@backup.command("session-delete")
@click.argument("session_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def session_delete(ctx: click.Context, session_id: str, yes: bool) -> None:
    """Delete a backup session."""
    if not yes:
        click.confirm(f"Delete session {session_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/sessions/{session_id}")
    console.print(f"[green]Session {session_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Clients
# ══════════════════════════════════════════════════════════════════════════

@backup.command("client-list")
@click.option("--limit", type=int, default=None, help="Max results.")
@output_options
@click.pass_context
def client_list(ctx: click.Context, limit: int | None, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """List registered backup clients (agents)."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_freezer(client)}/v2/clients", params=params)

    clients = data.get("clients", []) if isinstance(data, dict) else data

    print_list(
        clients,
        [
            ("Client ID", "client_id", {"style": "cyan", "no_wrap": True}),
            ("Hostname", lambda c: c.get("hostname", "") or "—", {"style": "bold"}),
            ("Description", lambda c: c.get("description", "") or "—"),
            ("UUID", lambda c: c.get("uuid", "") or "—", {"style": "dim"}),
        ],
        title="Backup Clients",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No clients found.",
    )


@backup.command("client-show")
@click.argument("client_id")
@output_options
@click.pass_context
def client_show(ctx: click.Context, client_id: str, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """Show backup client details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_freezer(client)}/v2/clients/{client_id}")

    fields = [(key, str(data.get(key, "") or "")) for key in
              ["client_id", "hostname", "description", "uuid",
               "user_id", "project_id"]]

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@backup.command("client-register")
@click.argument("hostname")
@click.option("--description", default="", help="Client description.")
@click.pass_context
def client_register(ctx: click.Context, hostname: str, description: str) -> None:
    """Register a new backup client."""
    client = ctx.find_object(OrcaContext).ensure_client()
    body = {"client_id": hostname, "hostname": hostname, "description": description}
    data = client.post(f"{_freezer(client)}/v2/clients", json=body)
    cid = data.get("client_id", "") if data else ""
    console.print(f"[green]Client '{hostname}' registered ({cid}).[/green]")


@backup.command("client-delete")
@click.argument("client_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def client_delete(ctx: click.Context, client_id: str, yes: bool) -> None:
    """Unregister a backup client."""
    if not yes:
        click.confirm(f"Delete client {client_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/clients/{client_id}")
    console.print(f"[green]Client {client_id} deleted.[/green]")


# ══════════════════════════════════════════════════════════════════════════
#  Actions
# ══════════════════════════════════════════════════════════════════════════

@backup.command("action-list")
@click.option("--limit", type=int, default=None, help="Max results.")
@output_options
@click.pass_context
def action_list(ctx: click.Context, limit: int | None, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """List backup actions."""
    client = ctx.find_object(OrcaContext).ensure_client()
    params: dict = {}
    if limit:
        params["limit"] = limit
    data = client.get(f"{_freezer(client)}/v2/actions", params=params)

    actions = data.get("actions", []) if isinstance(data, dict) else data

    print_list(
        actions,
        [
            ("Action ID", "action_id", {"style": "cyan", "no_wrap": True}),
            ("Action", lambda a: a.get("freezer_action", {}).get("action", "") or "—", {"style": "bold"}),
            ("Path", lambda a: a.get("freezer_action", {}).get("path_to_backup", "") or a.get("freezer_action", {}).get("restore_abs_path", "") or "—"),
            ("Storage", lambda a: a.get("freezer_action", {}).get("storage", "") or "—"),
            ("Mode", lambda a: a.get("freezer_action", {}).get("mode", "") or "—"),
        ],
        title="Backup Actions",
        output_format=output_format, fit_width=fit_width, max_width=max_width, noindent=noindent,
        columns=columns,
        empty_msg="No actions found.",
    )


@backup.command("action-show")
@click.argument("action_id")
@output_options
@click.pass_context
def action_show(ctx: click.Context, action_id: str, output_format: str,
                columns: tuple[str, ...], fit_width: bool, max_width: int | None,
                noindent: bool) -> None:
    """Show backup action details."""
    client = ctx.find_object(OrcaContext).ensure_client()
    data = client.get(f"{_freezer(client)}/v2/actions/{action_id}")

    fa = data.get("freezer_action", {})
    fields = [
        ("Action ID", data.get("action_id", "")),
        ("User ID", data.get("user_id", "")),
        ("Project ID", data.get("project_id", "")),
    ]
    for key in ["action", "path_to_backup", "restore_abs_path", "container",
                "storage", "mode", "engine_name", "backup_name",
                "max_level", "max_retries", "no_incremental",
                "log_file", "hostname_dir_to_backup"]:
        val = fa.get(key)
        if val is not None and val != "":
            fields.append((key, str(val)))

    print_detail(fields, output_format=output_format, fit_width=fit_width,
                 max_width=max_width, noindent=noindent, columns=columns)


@backup.command("action-create")
@click.option("--action", "action_type", type=click.Choice(["backup", "restore", "admin"]),
              default="backup", show_default=True)
@click.option("--path", "path_to_backup", required=True, help="Path to back up or restore.")
@click.option("--container", default=None, help="Swift container name.")
@click.option("--storage", type=click.Choice(["swift", "local", "ssh", "s3"]),
              default="swift", show_default=True)
@click.option("--mode", type=click.Choice(["fs", "mysql", "mongo", "mssql", "cinder", "nova"]),
              default="fs", show_default=True)
@click.option("--backup-name", default=None, help="Name for the backup.")
@click.option("--max-level", type=int, default=None, help="Max incremental backup level.")
@click.pass_context
def action_create(ctx: click.Context, action_type: str, path_to_backup: str,
                  container: str | None, storage: str, mode: str,
                  backup_name: str | None, max_level: int | None) -> None:
    """Create a standalone backup action.

    \b
    Examples:
      orca backup action-create --path /var/data --container my-backups
      orca backup action-create --action restore --path /var/data --container my-backups
      orca backup action-create --path /var/lib/mysql --mode mysql --backup-name daily-mysql
    """
    client = ctx.find_object(OrcaContext).ensure_client()

    fa: dict = {
        "action": action_type,
        "mode": mode,
        "storage": storage,
    }
    if action_type == "backup":
        fa["path_to_backup"] = path_to_backup
    else:
        fa["restore_abs_path"] = path_to_backup
    if container:
        fa["container"] = container
    if backup_name:
        fa["backup_name"] = backup_name
    if max_level is not None:
        fa["max_level"] = max_level

    data = client.post(f"{_freezer(client)}/v2/actions", json={"freezer_action": fa})
    aid = data.get("action_id", "") if data else ""
    console.print(f"[green]Action created ({aid}).[/green]")


@backup.command("action-delete")
@click.argument("action_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def action_delete(ctx: click.Context, action_id: str, yes: bool) -> None:
    """Delete a backup action."""
    if not yes:
        click.confirm(f"Delete action {action_id}?", abort=True)
    client = ctx.find_object(OrcaContext).ensure_client()
    client.delete(f"{_freezer(client)}/v2/actions/{action_id}")
    console.print(f"[green]Action {action_id} deleted.[/green]")
