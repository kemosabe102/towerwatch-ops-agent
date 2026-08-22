"""Startup configuration — the boot-time gates.

A misconfigured server should refuse to start with a message naming the setting that
is wrong. `config.py` had this for `TOWERWATCH_MODE` and not for the manifest path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from towerwatch_ops_agent.config import (
    DEFAULT_FIXTURE_MANIFEST,
    MODE_FIXTURE,
    MODE_LIVE,
    ServerConfig,
)


def test_defaults_to_fixture_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live mode needs a client that does not exist, so defaulting there would not boot."""
    monkeypatch.delenv("TOWERWATCH_MODE", raising=False)
    monkeypatch.delenv("TOWERWATCH_FIXTURE_MANIFEST", raising=False)
    config = ServerConfig.from_env()

    assert config.mode == MODE_FIXTURE
    assert config.fixture_manifest == DEFAULT_FIXTURE_MANIFEST


def test_an_unknown_mode_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOWERWATCH_MODE", "prod")
    with pytest.raises(ValueError, match="TOWERWATCH_MODE"):
        ServerConfig.from_env()


def test_mode_is_case_and_whitespace_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOWERWATCH_MODE", "  FIXTURE  ")
    monkeypatch.delenv("TOWERWATCH_FIXTURE_MANIFEST", raising=False)
    assert ServerConfig.from_env().mode == MODE_FIXTURE


def test_a_manifest_path_that_does_not_exist_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Regression: this died on a bare FileNotFoundError naming no setting at all.

    An operator saw a path and an errno, with nothing connecting either to the
    variable that produced them — unlike TOWERWATCH_MODE two lines above.
    """
    monkeypatch.setenv("TOWERWATCH_MODE", MODE_FIXTURE)
    monkeypatch.setenv("TOWERWATCH_FIXTURE_MANIFEST", str(tmp_path / "absent.yaml"))

    with pytest.raises(ValueError, match="TOWERWATCH_FIXTURE_MANIFEST"):
        ServerConfig.from_env()


def test_a_valid_manifest_override_is_accepted(
    monkeypatch: pytest.MonkeyPatch, stub_manifest_path: Path
) -> None:
    monkeypatch.setenv("TOWERWATCH_MODE", MODE_FIXTURE)
    monkeypatch.setenv("TOWERWATCH_FIXTURE_MANIFEST", str(stub_manifest_path))
    assert ServerConfig.from_env().fixture_manifest == stub_manifest_path


def test_live_mode_does_not_require_a_fixture_corpus(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The corpus check is fixture mode's concern; live mode fails later, in build_client."""
    monkeypatch.setenv("TOWERWATCH_MODE", MODE_LIVE)
    monkeypatch.setenv("TOWERWATCH_FIXTURE_MANIFEST", str(tmp_path / "absent.yaml"))
    assert ServerConfig.from_env().mode == MODE_LIVE
