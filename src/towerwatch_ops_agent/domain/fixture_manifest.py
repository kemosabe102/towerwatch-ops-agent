"""Pydantic models for the fixture manifest (`docs/design/10-fixture-manifest.md`).

This is the loader, not the schema owner — the design doc is authoritative. Fields are
required here wherever the doc calls them mandatory, so a corpus missing `provenance`
fails at load rather than silently becoming unlabeled synthetic data.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="after")
    def _absence_and_presence_are_exclusive(self) -> FixtureWindow:
        """A group cannot be both collected and deliberately absent.

        Without this the query path resolves the contradiction silently: the absence
        check runs first and wins, so the `groups_present` entry becomes unreachable
        configuration with no error. A curator who fat-fingers a group into both lists
        would get a window that behaves as if they had only listed it absent. The whole
        value of `groups_absent` is being an honest record, so an ambiguous one fails
        at load like every other malformed field.
        """
        overlap = sorted(
            group.value
            for group in {entry.group for entry in self.groups_absent} & set(self.groups_present)
        )
        if overlap:
            raise ValueError(
                f"Window {self.id!r} lists {overlap} in both groups_present and "
                "groups_absent. A group is either collected here or documented as "
                "absent — never both."
            )
        return self

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

    @model_validator(mode="after")
    def _windows_do_not_overlap_within_a_group(self) -> FixtureManifest:
        """Two windows may not cover the same site, group, and instant.

        The query path concatenates every collecting window's samples and buckets the
        result, so two windows overlapping on one group silently average their values
        together — a curator mistake becomes a number that appears in neither source
        and carries no note saying so. Windows are a curated artifact; an ambiguous
        one is a corpus bug, and the corpus is exactly where it should be caught.
        """
        for i, first in enumerate(self.windows):
            for second in self.windows[i + 1 :]:
                if first.site != second.site:
                    continue
                if first.start >= second.end or second.start >= first.end:
                    continue
                shared = sorted(
                    group.value for group in set(first.groups_present) & set(second.groups_present)
                )
                if shared:
                    raise ValueError(
                        f"Windows {first.id!r} and {second.id!r} both cover site "
                        f"{first.site!r} over an overlapping time range and both "
                        f"collect {shared}. Their samples would be averaged together "
                        "into values present in neither window."
                    )
        return self

    @model_validator(mode="after")
    def _window_ids_are_unique(self) -> FixtureManifest:
        """Ids address windows in the answer key, so a duplicate is an ambiguous key."""
        counts = Counter(window.id for window in self.windows)
        duplicates = sorted(window_id for window_id, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"Duplicate window id(s) in manifest: {duplicates}.")
        return self

    @classmethod
    def load(cls, manifest_path: Path) -> FixtureManifest:
        """Load and validate a corpus, including that every payload it names exists.

        Payload existence is checked here rather than on the model because only the
        caller knows the manifest's directory, and paths are relative to it. Checking
        at load is the point: a missing payload otherwise surfaces as a bare
        `FileNotFoundError` from deep inside a query, which points a curator at the
        query rather than at the manifest entry that is actually wrong — and stays
        invisible entirely for any window a given run never happens to touch.
        """
        with manifest_path.open(encoding="utf-8") as fh:
            manifest = cls.model_validate(yaml.safe_load(fh))

        missing = [
            (window.id, window.payload)
            for window in manifest.windows
            if window.payload is not None and not (manifest_path.parent / window.payload).is_file()
        ]
        if missing:
            listed = ", ".join(f"{wid} -> {path}" for wid, path in missing)
            raise ValueError(
                f"Manifest {str(manifest_path)!r} names payload files that do not "
                f"exist: {listed}. Paths are relative to the manifest's directory."
            )
        return manifest

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
            (
                SeriesPoint(ts=datetime.fromisoformat(ts), value=float(value))
                for ts, value in points
            ),
            key=lambda point: point.ts,
        )
        for name, points in raw.items()
    }
