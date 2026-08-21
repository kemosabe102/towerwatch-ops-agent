"""Domain layer: data access behind a Protocol, plus the shared vocabulary.

Dual-mode per ADR-0002 — `GrafanaCloudClient` (live) and `FixtureClient` (curated)
are both intended to satisfy the same `DataClient` Protocol. Neither exists yet: this
module defines the seam only. `FixtureClient` lands next; `GrafanaCloudClient` is not
scheduled for Phase 1.
"""
