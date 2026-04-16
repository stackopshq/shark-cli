# Getting Started

## Requirements

- Python 3.9+
- An OpenStack account with API credentials

## Installation

=== "pip"

    ```bash
    pip install .
    ```

=== "Poetry"

    ```bash
    poetry install
    ```

After installation the `orca` command is available globally.

## Configuration

### Interactive setup

```bash
orca setup
```

This prompts for all fields and stores them in `~/.orca/config.yaml` (permissions `600`).

### Profiles

orca supports multiple named profiles for managing several clouds:

```bash
orca profile add         # add a new profile interactively
orca profile list        # list all profiles
orca profile switch prod # switch active profile
orca --profile dev server list  # use a specific profile for one command
```

### Import from clouds.yaml

```bash
orca profile from-clouds mycloud
```

### Environment variables

Standard OpenStack `OS_*` variables are supported:

```bash
export OS_AUTH_URL="https://keystone.example.com:5000/v3"
export OS_USERNAME="myuser"
export OS_PASSWORD="mypassword"
export OS_USER_DOMAIN_NAME="Default"
export OS_PROJECT_NAME="myproject"
```

!!! tip
    Priority: `--profile` flag > `OS_*` env vars > `OS_CLOUD` → `clouds.yaml` > active orca profile.

## Shell Auto-Completion

=== "Bash"

    Add to `~/.bashrc`:

    ```bash
    eval "$(_ORCA_COMPLETE=bash_source orca)"
    ```

=== "Zsh"

    Add to `~/.zshrc`:

    ```zsh
    eval "$(_ORCA_COMPLETE=zsh_source orca)"
    ```

=== "Fish"

    ```fish
    _ORCA_COMPLETE=fish_source orca > ~/.config/fish/completions/orca.fish
    ```

You can also run `orca completion <shell>` to display these instructions.

## Verify Installation

```bash
orca --version
orca catalog        # List available service endpoints
orca server list    # List your compute instances
```

## Next Steps

Browse the [command reference](commands/index.md) for detailed usage of each service.
