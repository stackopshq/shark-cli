"""Shared Click context object for orca."""

from __future__ import annotations

from orca_cli.core.client import OrcaClient
from orca_cli.core.config import config_is_complete, load_config
from orca_cli.core.exceptions import OrcaCLIError


class OrcaContext:
    """Bag object attached to ``click.Context.obj`` to share state across commands."""

    def __init__(self) -> None:
        self.client: OrcaClient | None = None
        self.profile: str | None = None  # set by --profile flag
        self.region: str | None = None   # set by --region flag

    def ensure_client(self) -> OrcaClient:
        """Lazily build and return the API client, raising a clear error if
        credentials are missing."""
        if self.client is not None:
            return self.client

        config = load_config(profile_name=self.profile)
        if not config_is_complete(config):
            raise OrcaCLIError(
                "Incomplete configuration. Run 'orca setup' to provide your "
                "OpenStack credentials, or set OS_* environment variables, "
                "or configure a clouds.yaml file."
            )

        # Override region if --region flag was passed
        if self.region:
            config["region_name"] = self.region

        self.client = OrcaClient(config)
        return self.client
