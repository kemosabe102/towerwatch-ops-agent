"""Domain layer: data access behind a Protocol, plus the shared vocabulary.

Dual-mode per ADR-0002 — `GrafanaCloudClient` (live) and `FixtureClient` (curated)
satisfy the same `DataClient` Protocol. Only the fixture client exists this pass.
"""
