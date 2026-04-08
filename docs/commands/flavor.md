# Flavors — `shark flavor`

List available compute flavors (Nova). Flavors define the hardware profile for a server: number of vCPUs, RAM, and root disk size. Use this command to find the right flavor ID before creating a server.

---

## list

List all available flavors, sorted by vCPUs and RAM. Output columns: **ID**, **Name**, **vCPUs**, **RAM (MB)**, **Disk (GB)**.

```bash
shark flavor list
```

!!! tip
    A disk size of `0` means the flavor has no local disk — the server must boot from a Cinder volume (which `shark server create` does by default).
