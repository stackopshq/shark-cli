# Compute — `shark server`

Manage compute instances (Nova). This is the main command group for virtual machine lifecycle — creation, power management, resizing, snapshots, console access, and network/volume attachments.

---

## list

List all servers in the current project with their status, networks, and flavor.

```bash
shark server list
shark server list --limit 10
```

| Option | Default | Description |
|---|---|---|
| `--limit` | `50` | Max number of servers to return |

---

## show

Display detailed information about a specific server: ID, name, status, flavor, image, networks, key name, attached volumes, and timestamps.

```bash
shark server show <server-id>
```

---

## create

Create a new server (boot from volume). A Cinder volume is automatically created from the specified image and used as the boot disk.

```bash
shark server create \
  --name my-vm \
  --flavor <flavor-id> \
  --image <image-id> \
  --disk-size 30 \
  --network <network-id> \
  --key-name my-keypair \
  --security-group default
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--name` | yes | — | Server name |
| `--flavor` | yes | — | Flavor ID (`shark flavor list`) |
| `--image` | yes | — | Image ID (`shark image list`) |
| `--disk-size` | no | `20` | Boot volume size in GB |
| `--network` | no | — | Network ID (`shark network list`) |
| `--key-name` | no | — | SSH key pair name (`shark keypair list`) |
| `--security-group` | no | — | Security group name (repeatable) |

---

## delete

Permanently delete a server. Asks for confirmation unless `-y` is passed.

```bash
shark server delete <server-id>
shark server delete <server-id> -y
```

---

## start

Start a server that is in `SHUTOFF` status.

```bash
shark server start <server-id>
```

---

## stop

Gracefully shut down a running server. The server transitions to `SHUTOFF` status.

```bash
shark server stop <server-id>
```

---

## reboot

Reboot a server. A soft reboot sends an ACPI signal; a hard reboot power-cycles the VM.

```bash
shark server reboot <server-id>
shark server reboot <server-id> --hard
```

| Option | Description |
|---|---|
| `--hard` | Perform a hard (power-cycle) reboot |

---

## pause

Freeze a server in memory. The VM state is held in RAM on the hypervisor. Faster than suspend but uses host memory.

```bash
shark server pause <server-id>
```

---

## unpause

Resume a paused server from memory.

```bash
shark server unpause <server-id>
```

---

## suspend

Suspend a server to disk. The VM state is written to the hypervisor's disk, freeing RAM. Slower than pause but uses no host memory.

```bash
shark server suspend <server-id>
```

---

## resume

Resume a suspended server from disk.

```bash
shark server resume <server-id>
```

---

## lock

Lock a server to prevent non-admin users from performing destructive actions (delete, stop, reboot, etc.).

```bash
shark server lock <server-id>
```

---

## unlock

Unlock a previously locked server, restoring normal operations.

```bash
shark server unlock <server-id>
```

---

## rescue

Boot a server into rescue mode using a temporary rescue image. Useful for fixing boot issues, recovering data, or resetting passwords. Returns a temporary admin password.

```bash
shark server rescue <server-id>
shark server rescue <server-id> --image <rescue-image-id>
shark server rescue <server-id> --password mypass
```

| Option | Description |
|---|---|
| `--image` | Rescue image ID (optional, uses default if omitted) |
| `--password` | Admin password for rescue mode |

---

## unrescue

Exit rescue mode and reboot the server with its original boot disk.

```bash
shark server unrescue <server-id>
```

---

## shelve

Shelve a server: take a snapshot, then shut it down and free hypervisor resources. Useful for long-term idle servers to reduce costs.

```bash
shark server shelve <server-id>
```

---

## unshelve

Restore a shelved server — re-provision it from the snapshot and boot it.

```bash
shark server unshelve <server-id>
```

---

## resize

Resize a server to a different flavor (change vCPUs, RAM, disk). The server enters `VERIFY_RESIZE` status and must be confirmed or reverted.

```bash
shark server resize <server-id> --flavor <new-flavor-id>
```

| Option | Required | Description |
|---|---|---|
| `--flavor` | yes | Target flavor ID |

---

## confirm-resize

Confirm a pending resize. The original resources are freed.

```bash
shark server confirm-resize <server-id>
```

---

## revert-resize

Revert a pending resize and restore the original flavor.

```bash
shark server revert-resize <server-id>
```

!!! tip "Resize workflow"
    ```
    resize → VERIFY_RESIZE → confirm-resize  (keep new flavor)
                            → revert-resize   (rollback)
    ```

---

## rebuild

Reinstall a server with a new image. The server keeps its ID, IPs, and volumes, but the root disk is replaced. **Destructive** — asks for confirmation.

```bash
shark server rebuild <server-id> --image <new-image-id>
shark server rebuild <server-id> --image <id> --name new-name --password newpass -y
```

| Option | Required | Description |
|---|---|---|
| `--image` | yes | New image ID |
| `--name` | no | New server name |
| `--password` | no | New admin password |
| `-y` | no | Skip confirmation |

---

## rename

Rename a server without affecting its state or configuration.

```bash
shark server rename <server-id> new-name
```

---

## create-image

Create a snapshot image from a running or stopped server. The image appears in `shark image list` once complete.

```bash
shark server create-image <server-id> my-snapshot
```

---

## password

Retrieve and decrypt the server's admin password. The password is encrypted with your SSH public key at boot and decrypted locally with your private key (RSA only).

```bash
shark server password <server-id>
shark server password <server-id> --key ~/.ssh/my-key.pem
shark server password <server-id> --raw   # print encrypted base64
```

| Option | Description |
|---|---|
| `--key` | Path to RSA private key (auto-detected from `~/.ssh/shark-*` if omitted) |
| `--raw` | Print encrypted password without decrypting |

---

## console-log

Display the server's boot console output (serial log). Useful for debugging boot failures.

```bash
shark server console-log <server-id>
shark server console-log <server-id> --lines 100
shark server console-log <server-id> --lines 0   # all output
```

| Option | Default | Description |
|---|---|---|
| `--lines` | `50` | Number of lines to retrieve (0 = all) |

---

## console-url

Get a URL to access the server's graphical console (VNC, SPICE, or serial) in your browser.

```bash
shark server console-url <server-id>
shark server console-url <server-id> --type spice-html5
shark server console-url <server-id> --type serial
```

| Option | Default | Choices |
|---|---|---|
| `--type` | `novnc` | `novnc`, `xvpvnc`, `spice-html5`, `rdp-html5`, `serial` |

---

## attach-volume

Attach a Cinder volume to a server. The volume appears as a block device inside the VM.

```bash
shark server attach-volume <server-id> <volume-id>
shark server attach-volume <server-id> <volume-id> --device /dev/vdc
```

| Option | Description |
|---|---|
| `--device` | Device name (e.g. `/dev/vdb`). Auto-assigned if omitted |

---

## detach-volume

Detach a volume from a server. The volume returns to `available` status.

```bash
shark server detach-volume <server-id> <volume-id>
```

---

## list-volumes

List all volumes currently attached to a server with their device names.

```bash
shark server list-volumes <server-id>
```

---

## attach-interface

Attach a network interface (port) to a running server. You can attach an existing port or let Neutron create one on a specified network.

```bash
shark server attach-interface <server-id> --port-id <port-id>
shark server attach-interface <server-id> --net-id <network-id>
shark server attach-interface <server-id> --net-id <network-id> --fixed-ip 10.0.0.50
```

| Option | Description |
|---|---|
| `--port-id` | Existing port ID to attach |
| `--net-id` | Network ID (creates a new port automatically) |
| `--fixed-ip` | Fixed IP for the new port (requires `--net-id`) |

---

## detach-interface

Detach a network interface (port) from a server.

```bash
shark server detach-interface <server-id> <port-id>
```

---

## list-interfaces

List all network interfaces attached to a server with port IDs, network IDs, IPs, and MAC addresses.

```bash
shark server list-interfaces <server-id>
```
