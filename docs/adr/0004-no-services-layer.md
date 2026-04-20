# ADR-0004: No services layer (yet)

**Status**: Accepted
**Date**: 2026-04-20

## Context

orca's commands today call `OrcaClient.{get,post,put,patch,delete}`
directly and build their own URLs (`f"{client.compute_url}/servers/{id}"`).
58 of the 63 command modules do this — about 740 raw HTTP calls
scattered across the CLI handlers.

A "clean" architecture would interpose a services layer:
`orca_cli/services/server.py` exposing `list_servers()`, `create_server()`,
etc., with commands becoming thin handlers that delegate to the service
and format the result. That layer would:

- Centralise URL construction (no more `/v2.0`, `/detail` magic strings
  scattered).
- Make commands testable without mocking a full HTTP client.
- Enable reuse from a future Python API or web UI.

The cost is significant: ~63 commands × ~10 endpoints each = several
hundred service methods, each with corresponding TypedDicts and tests. A
multi-week refactor across the entire surface.

## Decision

We do **not** introduce a services layer at this stage. Commands continue
to call the HTTP client directly. The decision is reviewed each quarter.

The criteria for revisiting:

- A second consumer (web UI, library, another CLI) needs the same logic.
- HTTP-call duplication crosses ~5 occurrences of the same endpoint —
  centralise that single endpoint, not the whole layer.
- A breaking OpenStack API change forces touching >20 commands —
  introduce the layer for the affected service first.

Until then we accept the dette: tests mock at the `OrcaClient` boundary
(see `tests/conftest.py::mock_client`), and that boundary is stable
enough to make this practical.

## Consequences

- **Positive**: shipping new commands is fast — one file, one
  `@click.command`, no service plumbing.
- **Positive**: only one abstraction (`OrcaClient`) to keep stable.
- **Negative / trade-off**: command modules mix HTTP details with
  presentation concerns; refactoring an endpoint requires grepping the
  whole `commands/` tree.
- **Negative / trade-off**: tests have to be aware of the URL each
  command calls — `mock_client` returns a generic mock and tests assert
  on `client.get.call_args`. Less robust than asserting on
  `service.list_servers.call_args`.
- **Negative**: see also ADR-0005 (typed models) — the services layer is
  a prerequisite for proper return-type modelling. Both decisions stand
  or fall together.
