# `orca server` — server

Manage compute servers.

---

## add-fixed-ip

NETWORK_ID

```bash
orca server add-fixed-ip [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## add-network

NETWORK_ID

```bash
orca server add-network [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## add-port

Attach an existing Neutron port to a server.

```bash
orca server add-port [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## add-security-group

SECURITY_GROUP

```bash
orca server add-security-group [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## attach-interface

Attach a network interface (port) to a server.

```bash
orca server attach-interface [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--port-id TEXT` | Existing port ID to attach. |
| `--net-id TEXT` | Network ID (creates a new port automatically). |
| `--fixed-ip TEXT` | Fixed IP for the new port (requires --net-id). |
| `--help` | Show this message and exit. |

---

## attach-volume

VOLUME_ID

```bash
orca server attach-volume [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--device TEXT` | Device name (e.g. /dev/vdb). Auto-assigned if omitted. |
| `--help` | Show this message and exit. |

---

## bulk

{start|stop|reboot|delete}

```bash
orca server bulk [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Filter by name (supports wildcards: dev-*). |
| `--status TEXT` | Filter by status (e.g. ERROR, SHUTOFF). |
| `--all` | Select all servers (use with caution). |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## clone

Clone a server — recreate one with the same config.

```bash
orca server clone [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Name for the cloned server.  [required] |
| `--disk-size INTEGER` | Boot volume size in GB. Default: same as source. |
| `--help` | Show this message and exit. |

---

## confirm-resize

Confirm a pending resize.

```bash
orca server confirm-resize [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## console-log

Show the server console output (boot log).

```bash
orca server console-log [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--lines INTEGER` | Number of lines to retrieve (0 = all).  [default: 50] |
| `--help` | Show this message and exit. |

---

## console-url

Get a URL to access the server console (VNC/SPICE/serial).

```bash
orca server console-url [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type [novnc|xvpvnc|spice-html5|rdp-html5|serial]` | |
| `--open` | Open the URL in the default system browser |
| `--help` | Show this message and exit. |

---

## create

Create a new server (boot from volume).

```bash
orca server create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Server name. |
| `--flavor TEXT` | Flavor ID (see 'orca flavor list'). |
| `--image TEXT` | Image ID (see 'orca image list'). |
| `--disk-size INTEGER` | Boot volume size in GB.  [default: 20] |
| `--network TEXT` | Network ID (see 'orca network list'). |
| `--key-name TEXT` | SSH key pair name (see 'orca keypair list'). |
| `--security-group TEXT` | Security group name (repeatable). |
| `--wait` | Wait until the server reaches ACTIVE status. |
| `-i, --interactive` | Step-by-step wizard — browse images, flavors, and |
| `--help` | Show this message and exit. |

---

## create-image

IMAGE_NAME

```bash
orca server create-image [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## delete

Delete a server.

```bash
orca server delete [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation. |
| `--dry-run` | Show what would be deleted without deleting. |
| `--wait` | Wait until the server is fully deleted. |
| `--help` | Show this message and exit. |

---

## detach-interface

PORT_ID

```bash
orca server detach-interface [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## detach-volume

VOLUME_ID

```bash
orca server detach-volume [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## diff

Compare two servers side by side.

```bash
orca server diff [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## dump-create

Trigger a crash dump on a server (requires Nova microversion ≥ 2.17).

```bash
orca server dump-create [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## evacuate

Evacuate a server from a failed host to another.

```bash
orca server evacuate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Target host (admin only, optional). |
| `--on-shared-storage / --no-shared-storage` | |
| `--password TEXT` | Admin password for the evacuated server. |
| `--help` | Show this message and exit. |

---

## list

List servers.

```bash
orca server list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit INTEGER` | Max number of servers to return.  [default: |
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## list-interfaces

List network interfaces attached to a server.

```bash
orca server list-interfaces [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## list-volumes

List volumes attached to a server.

```bash
orca server list-volumes [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## live-migrate

Live-migrate a server without downtime.

```bash
orca server live-migrate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Target host (admin only, optional). |
| `--block-migration / --no-block-migration` | |
| `--help` | Show this message and exit. |

---

## lock

Lock a server (prevent actions by non-admin).

```bash
orca server lock [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## metadata-list

Show all metadata key/value pairs for a server.

```bash
orca server metadata-list [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## migrate

Cold-migrate a server to another host.

```bash
orca server migrate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host TEXT` | Target host (admin only, optional). |
| `--help` | Show this message and exit. |

---

## migration-abort

MIGRATION_ID

```bash
orca server migration-abort [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## migration-force-complete

[OPTIONS] SERVER_ID MIGRATION_ID

```bash
orca server migration-force-complete [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## migration-list

List migrations for a server.

```bash
orca server migration-list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## migration-show

MIGRATION_ID

```bash
orca server migration-show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## password

Retrieve and decrypt the server admin password.

```bash
orca server password [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--key PATH` | Path to the RSA private key used to decrypt. Tries ~/.ssh/orca-* |
| `--raw` | Print the encrypted password without decrypting. |
| `--help` | Show this message and exit. |

---

## pause

Pause a server (freeze in memory).

```bash
orca server pause [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## port-forward

PORT_MAPPING

```bash
orca server port-forward [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-u, --user TEXT` | SSH user. Default: 'root'. |
| `-i, --key PATH` | Private key path. |
| `-p, --ssh-port INTEGER` | SSH port on the server.  [default: 22] |
| `-R, --reverse` | Reverse tunnel (remote → local). |
| `-b, --background` | Run tunnel in background (-f -N). |
| `--help` | Show this message and exit. |

---

## reboot

Reboot a server.

```bash
orca server reboot [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--hard` | Perform a hard reboot. |
| `--wait` | Wait until the server reaches ACTIVE status. |

---

## rebuild

Rebuild a server with a new image (reinstall).

```bash
orca server rebuild [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--image TEXT` | New image ID.  [required] |
| `--name TEXT` | New server name (optional). |
| `--password TEXT` | New admin password (optional). |
| `-y, --yes` | Skip confirmation. |
| `--help` | Show this message and exit. |

---

## remove-fixed-ip

IP_ADDRESS

```bash
orca server remove-fixed-ip [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## remove-network

NETWORK_ID

```bash
orca server remove-network [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## remove-port

Detach a Neutron port from a server.

```bash
orca server remove-port [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## remove-security-group

[OPTIONS] SERVER_ID SECURITY_GROUP

```bash
orca server remove-security-group [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## rename

Rename a server.

```bash
orca server rename [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## rescue

Put a server in rescue mode.

```bash
orca server rescue [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--image TEXT` | Rescue image ID (optional). |
| `--password TEXT` | Admin password for rescue mode. |
| `--help` | Show this message and exit. |

---

## resize

Resize a server to a new flavor.

```bash
orca server resize [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--flavor TEXT` | Target flavor ID.  [required] |
| `--help` | Show this message and exit. |

---

## restore

Restore a soft-deleted server.

```bash
orca server restore [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## resume

Resume a suspended server.

```bash
orca server resume [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## revert-resize

Revert a pending resize (restore original flavor).

```bash
orca server revert-resize [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## set

Set server properties, metadata, tags, or admin password.

```bash
orca server set [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | New display name. |
| `--property KEY=VALUE` | Metadata key=value (repeatable). |
| `--tag TEXT` | Tag to set (repeatable, replaces all existing tags). |
| `--admin-password TEXT` | New admin/root password (injected via Nova). |
| `--help` | Show this message and exit. |

---

## shelve

Shelve a server (snapshot + shut down, frees resources).

```bash
orca server shelve [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## show

Show server details.

```bash
orca server show [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--noindent` | Disable JSON indentation. |
| `--max-width INTEGER` | Maximum table width (0 = unlimited). |
| `--fit-width` | Fit table to terminal width. |
| `-c, --column TEXT` | Column to include (repeatable). Shows all if |
| `-f, --format [table|json|value]` | |
| `--help` | Show this message and exit. |

---

## snapshot

Snapshot a server AND all its attached volumes.

```bash
orca server snapshot [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--name TEXT` | Snapshot name prefix. Default: server name. |
| `--help` | Show this message and exit. |

---

## ssh

SSH into a server by name or ID.

```bash
orca server ssh [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-u, --user TEXT` | SSH user. Default: auto-detect from image or 'root'. |
| `-i, --key PATH` | Private key path. |
| `-p, --port INTEGER` | SSH port.  [default: 22] |
| `--extra TEXT` | Extra SSH options (e.g. '-o StrictHostKeyChecking=no'). |
| `--help` | Show this message and exit. |

---

## start

Start (resume) a stopped server.

```bash
orca server start [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--wait` | Wait until the server reaches ACTIVE status. |

---

## stop

Stop (shut down) a server.

```bash
orca server stop [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--wait` | Wait until the server reaches SHUTOFF status. |

---

## suspend

Suspend a server (save to disk).

```bash
orca server suspend [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## tag-list

List tags on a server.

```bash
orca server tag-list [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## unlock

Unlock a locked server.

```bash
orca server unlock [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## unpause

Unpause a paused server.

```bash
orca server unpause [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## unrescue

Exit rescue mode.

```bash
orca server unrescue [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## unset

Remove metadata keys or tags from a server.

```bash
orca server unset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--property KEY` | Metadata key to remove (repeatable). |
| `--tag TEXT` | Tag to remove (repeatable). |
| `--help` | Show this message and exit. |

---

## unshelve

Unshelve (restore) a shelved server.

```bash
orca server unshelve [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## wait

Wait for a server to reach a target status.

```bash
orca server wait [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--status TEXT` | Target status to wait for.  [default: ACTIVE] |
| `--timeout INTEGER` | Timeout in seconds.  [default: 300] |
| `--interval INTEGER` | Poll interval in seconds.  [default: 5] |
| `--help` | Show this message and exit. |

---
