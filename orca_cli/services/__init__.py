"""Service layer — high-level operations on OpenStack resources.

Each service wraps an OrcaClient and exposes typed methods that map to
the underlying API endpoints. Command handlers in ``orca_cli/commands/``
delegate to a service rather than calling ``client.get/post/...``
directly; the trade-offs are documented in ADR-0007.

Services are introduced incrementally — only the resources whose
command modules have been migrated have a corresponding service yet.
"""
