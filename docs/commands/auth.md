# `orca auth` — auth

Keystone identity & access diagnostics.

---

## check

Verify credentials are still valid (password check).

```bash
orca auth check [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-a, --all` | Check all profiles, not just the active one. |
| `--clouds` | Also check clouds.yaml entries. |
| `--help` | Show this message and exit. |

---

## token-debug

Inspect the current token — roles, catalog, methods, expiration.

```bash
orca auth token-debug [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--raw` | Print the full token body as JSON. |

---

## token-revoke

Revoke a token.

```bash
orca auth token-revoke [OPTIONS]
```

| Option | Description |
|--------|-------------|

---

## whoami

Show current identity — user, project, roles, endpoints.

```bash
orca auth whoami [OPTIONS]
```

| Option | Description |
|--------|-------------|

---
