"""Pydantic models for the fixture manifest (`docs/design/10-fixture-manifest.md`).

This is the loader, not the schema owner — the design doc is authoritative. Fields are
required here wherever the doc calls them mandatory, so a corpus missing `provenance`
fails at load rather than silently becoming unlabeled synthetic data.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from towerwatch_ops_agent.domain.models import MetricGroup
from towerwatch_ops_agent.domain.protocol import SeriesPoint


class Provenance(str, Enum):
    """Mandatory per window. `synthetic` is permitted but never silently."""

    exported = "exported"
    reconstructed = "reconstructed"
    synthetic = "synthetic"


class WindowRole(str, Enum):
    """A kind, not a slot — several windows may share a role."""

    incident = "incident"
    reference = "reference"
    boundary = "boundary"


class AbsentGroup(BaseModel):
    """A deliberate absence with its reason — the `not_collected` evidence."""

    group: MetricGroup
    reason: str


class FixtureWindow(BaseModel):
    id: str
    site: str
    start: datetime
    end: datetime
    role: WindowRole
    provenance: Provenance
    resolution: str
    payload: str | None = None
    groups_present: list[MetricGroup] = Field(default_factory=list)
    groups_absent: list[AbsentGroup] = Field(default_factory=list)
    expected_findings: dict = Field(default_factory=dict)

    def absent_reason(self, group: MetricGroup) -> str | None:
        """The documented reason this group is absent, or None if it is not absent."""
        for entry in self.groups_absent:
            if entry.group == group:
                return entry.reason
        return None


class FixtureManifest(BaseModel):
    """The corpus root. `fixture_now` is the frozen clock the server reads at startup."""

    fixture_now: datetime
    generated_at: datetime
    pseudonym_scheme: str
    windows: list[FixtureWindow]

    @classmethod
    def load(cls, manifest_path: Path) -> FixtureManifest:
        with manifest_path.open(encoding="utf-8") as fh:
            return cls.model_validate(yaml.safe_load(fh))

    @property
    def sites(self) -> list[str]:
        """Configured sites, derived from the corpus — feeds the startup site enum."""
        seen: dict[str, None] = {}
        for window in self.windows:
            seen.setdefault(window.site, None)
        return list(seen)


def load_series(payload_path: Path) -> dict[str, list[SeriesPoint]]:
    """Read one window's series file.

    Format is `{metric_name: [[iso_timestamp, value], ...]}` — chosen for the stub and
    not yet a commitment for the real corpus (see `10-fixture-manifest.md`, open
    questions). Points are sorted on load so downsampling and pagination can both assume
    ordering rather than each re-establishing it.
    """
    with payload_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        name: sorted(
            (SeriesPoint(ts=datetime.fromisoformat(ts), value=float(value)) for ts, value in points),
            key=lambda point: point.ts,
        )
        for name, points in raw.items()
    }
