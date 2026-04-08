# Compute — `shark server`

Manage compute instances (Nova).

## Commands

| Command | Description |
|---|---|
| `list` | List servers |
| `show <id>` | Show server details |
| `create <name>` | Create a server |
| `delete <id>` | Delete a server |
| `start <id>` | Start a stopped server |
| `stop <id>` | Stop (shut down) a server |
| `reboot <id>` | Reboot a server |
| `rebuild <id>` | Rebuild with a new image |
| `resize <id>` | Resize to a new flavor |
| `confirm-resize <id>` | Confirm a pending resize |
| `revert-resize <id>` | Revert a pending resize |
| `rename <id> <name>` | Rename a server |
| `lock <id>` | Lock a server |
| `unlock <id>` | Unlock a server |
| `pause <id>` | Pause a server |
| `unpause <id>` | Unpause a server |
| `suspend <id>` | Suspend a server |
| `resume <id>` | Resume a suspended server |
| `rescue <id>` | Enter rescue mode |
| `unrescue <id>` | Exit rescue mode |
| `shelve <id>` | Shelve a server |
| `unshelve <id>` | Unshelve a server |
| `password <id>` | Retrieve admin password |
| `console <id>` | Open a VNC console URL |
| `list-volumes <id>` | List attached volumes |
| `list-interfaces <id>` | List network interfaces |
| `attach-interface <id>` | Attach a network interface |
| `detach-interface <id>` | Detach a network interface |

## Examples

### Create a server

```bash
shark server create my-vm \
  --flavor <flavor-id> \
  --image <image-id> \
  --network <network-id> \
  --keypair my-keypair \
  --security-group default
```

### Lifecycle operations

```bash
shark server stop <id>
shark server start <id>
shark server reboot <id> --hard
```

### Resize workflow

```bash
shark server resize <id> --flavor <new-flavor-id>
# Wait for VERIFY_RESIZE status
shark server confirm-resize <id>
# Or revert:
shark server revert-resize <id>
```

### Network interfaces

```bash
shark server list-interfaces <id>
shark server attach-interface <id> --net-id <network-id>
shark server detach-interface <id> --port-id <port-id>
```
