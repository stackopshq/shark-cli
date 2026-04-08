# Getting Started

## Requirements

- Python 3.9+
- A Sharktech Cloud account with API credentials

## Installation

=== "pip"

    ```bash
    pip install .
    ```

=== "Poetry"

    ```bash
    poetry install
    ```

After installation the `shark` command is available globally.

## Configuration

You need credentials from your **Sharktech Client Area** (cloud service information page):

| Field | Description | Example |
|---|---|---|
| **Auth URL** | Keystone endpoint | `https://cloud-xx.sharktech.net:5000` |
| **Username** | OpenStack user | `myuser` |
| **Password** | OpenStack password | — |
| **Domain ID** | OpenStack domain | `mydomain` |
| **Project ID** | OpenStack project | `myproject` |

### Interactive setup

```bash
shark setup
```

This prompts for all fields and stores them in `~/.shark/config.yaml` (permissions `600`).

### Environment variables

```bash
export SHARK_AUTH_URL="https://cloud-xx.sharktech.net:5000"
export SHARK_USERNAME="myuser"
export SHARK_PASSWORD="mypassword"
export SHARK_DOMAIN_ID="mydomain"
export SHARK_PROJECT_ID="myproject"
```

!!! tip
    Environment variables **always** take precedence over the config file.

## Shell Auto-Completion

=== "Bash"

    Add to `~/.bashrc`:

    ```bash
    eval "$(_SHARK_COMPLETE=bash_source shark)"
    ```

=== "Zsh"

    Add to `~/.zshrc`:

    ```zsh
    eval "$(_SHARK_COMPLETE=zsh_source shark)"
    ```

=== "Fish"

    ```fish
    _SHARK_COMPLETE=fish_source shark > ~/.config/fish/completions/shark.fish
    ```

You can also run `shark completion <shell>` to display these instructions.

## Verify Installation

```bash
shark --version
shark catalog        # List available service endpoints
shark server list    # List your compute instances
```

## Next Steps

Browse the [command reference](commands/index.md) for detailed usage of each service.
