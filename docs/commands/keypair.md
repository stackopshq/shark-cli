# Key Pairs — `shark keypair`

Manage SSH key pairs (Nova).

## Commands

| Command | Description |
|---|---|
| `list` | List key pairs |
| `show <name>` | Show key pair details (fingerprint & public key) |
| `create <name>` | Generate a new key pair (returns private key) |
| `upload <name>` | Import an existing public key |
| `generate <name>` | Generate locally and upload the public key |
| `delete <name>` | Delete a key pair |

## Examples

### Generate and save a key pair

```bash
shark keypair create my-key > ~/.ssh/my-key.pem
chmod 600 ~/.ssh/my-key.pem
```

### Upload an existing public key

```bash
shark keypair upload my-key --public-key ~/.ssh/id_rsa.pub
```
