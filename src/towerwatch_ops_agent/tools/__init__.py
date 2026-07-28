"""Tool implementations — one module per `towerwatch_*` tool.

Modules here depend on `domain.protocol.DataClient` only. Importing a concrete client
(`FixtureClient`, `GrafanaCloudClient`) would let a tool learn which mode it is running
in, which ADR-0002 forbids; `tests/tools/test_query_metrics.py` asserts this by parsing
the module's imports.
"""
