# Secrets — `shark secret`

Manage secrets & containers (Barbican key-manager).

## Secrets

| Command | Description |
|---|---|
| `list` | List secrets |
| `show <id>` | Show secret metadata |
| `create <name>` | Create a secret |
| `delete <id>` | Delete a secret |
| `get-payload <id>` | Retrieve secret payload |

## Containers

| Command | Description |
|---|---|
| `container-list` | List secret containers |
| `container-show <id>` | Show container details |
| `container-delete <id>` | Delete a container |

## Examples

### Store a password

```bash
shark secret create db-password \
  --payload "s3cret!" \
  --secret-type passphrase
```

### Store a symmetric key

```bash
shark secret create aes-key \
  --secret-type symmetric \
  --algorithm AES \
  --bit-length 256
```

### Retrieve a secret

```bash
shark secret get-payload <secret-id>
```

### Store a certificate with expiration

```bash
shark secret create tls-cert \
  --payload "$(cat cert.pem)" \
  --payload-content-type "application/x-pem-file" \
  --secret-type certificate \
  --expiration 2026-12-31T23:59:59
```

!!! warning
    Secret payloads are stored **encrypted at rest** in Barbican. The `get-payload` command retrieves the decrypted value — treat it as sensitive output.
