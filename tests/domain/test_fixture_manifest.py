"""Manifest validation — the load-time gates.

Pydantic covers what its type system reaches for free: required keys, enum members,
timestamps. These pin the checks it cannot express, all of which follow one rule from
the module docstring — a broken corpus fails at load, not deep inside a later query.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from towerwatch_ops_agent.domain.fixture_manifest import FixtureManifest


def _mutate(stub_manifest_path: Path, tmp_path: Path, mutate) -> Path:
    """Copy the stub corpus to tmp_path, apply `mutate` to the raw manifest dict."""
    raw = yaml.safe_load(stub_manifest_path.read_text(encoding="utf-8"))
    mutate(raw)
    for window in raw["windows"]:
        if window.get("payload"):
            source = stub_manifest_path.parent / window["payload"]
            target = tmp_path / window["payload"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_file():
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def test_the_committed_stub_corpus_loads(stub_manifest_path: Path) -> None:
    """The corpus in the repo must always be valid — this is the canary."""
    manifest = FixtureManifest.load(stub_manifest_path)
    assert manifest.windows
    assert manifest.fixture_now.tzinfo is not None


def test_a_group_cannot_be_both_present_and_absent(
    stub_manifest_path: Path, tmp_path: Path
) -> None:
    """Otherwise the query path resolves the contradiction silently, absence winning."""

    def mutate(raw: dict) -> None:
        raw["windows"][0]["groups_absent"] = [
            {"group": raw["windows"][0]["groups_present"][0], "reason": "contradiction"}
        ]

    with pytest.raises(ValidationError, match="never both"):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_a_payload_that_does_not_exist_fails_at_load(
    stub_manifest_path: Path, tmp_path: Path
) -> None:
    """Not at first query, where a bare FileNotFoundError blames the wrong thing."""

    def mutate(raw: dict) -> None:
        raw["windows"][0]["payload"] = "windows/absent.json"

    with pytest.raises(ValueError, match="do not exist"):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_duplicate_window_ids_are_rejected(stub_manifest_path: Path, tmp_path: Path) -> None:
    """Ids address windows in the answer key, so a duplicate is an ambiguous key."""

    def mutate(raw: dict) -> None:
        # Same id, but no group overlap — so this trips the id rule, not the
        # overlapping-windows rule.
        clone = dict(raw["windows"][0])
        clone["payload"] = None
        clone["groups_present"] = []
        raw["windows"].append(clone)

    with pytest.raises(ValidationError, match="Duplicate window id"):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_an_unknown_metric_group_is_rejected(stub_manifest_path: Path, tmp_path: Path) -> None:
    """Pydantic's own coverage, pinned: a typo'd group must not become a silent absence."""

    def mutate(raw: dict) -> None:
        raw["windows"][0]["groups_present"] = ["latencyy"]

    with pytest.raises(ValidationError):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_a_missing_provenance_is_rejected(stub_manifest_path: Path, tmp_path: Path) -> None:
    """The docstring's own example: unlabeled data must never load as if it were real."""

    def mutate(raw: dict) -> None:
        del raw["windows"][0]["provenance"]

    with pytest.raises(ValidationError):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_sites_are_deduplicated_across_windows(stub_manifest_path: Path, tmp_path: Path) -> None:
    """Many windows share a site, so `sites` is a dedupe — not a uniqueness violation."""

    def mutate(raw: dict) -> None:
        extra = dict(raw["windows"][0])
        extra["id"] = "another_window_same_site"
        extra["payload"] = None
        extra["groups_present"] = []
        raw["windows"].append(extra)

    manifest = FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))
    assert len(manifest.sites) == len(set(manifest.sites))


def test_overlapping_windows_sharing_a_group_are_rejected(
    stub_manifest_path: Path, tmp_path: Path
) -> None:
    """Otherwise their samples are averaged into values present in neither window."""

    def mutate(raw: dict) -> None:
        clone = dict(raw["windows"][0])
        clone["id"] = "overlapping_window"
        raw["windows"].append(clone)

    with pytest.raises(ValidationError, match="overlapping time range"):
        FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))


def test_adjacent_windows_sharing_a_group_are_allowed(
    stub_manifest_path: Path, tmp_path: Path
) -> None:
    """Half-open ranges: one window ending where the next begins is not an overlap."""

    def mutate(raw: dict) -> None:
        first = raw["windows"][0]
        following = dict(first)
        following["id"] = "the_next_hour"
        following["payload"] = None
        following["start"] = first["end"]
        following["end"] = "2026-07-14T02:00:00-07:00"
        raw["windows"].append(following)

    manifest = FixtureManifest.load(_mutate(stub_manifest_path, tmp_path, mutate))
    assert len(manifest.windows) == 3
