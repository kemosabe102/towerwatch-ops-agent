from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from towerwatch_ops_agent.domain.fixture_client import FixtureClient

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stub_manifest_path() -> Path:
    return REPO_ROOT / "fixtures" / "stub" / "manifest.yaml"


@pytest.fixture
def fixture_client(stub_manifest_path: Path) -> FixtureClient:
    return FixtureClient(stub_manifest_path)


@pytest.fixture
def window_start() -> datetime:
    return datetime.fromisoformat("2026-07-14T00:00:00-07:00")


@pytest.fixture
def window_end() -> datetime:
    return datetime.fromisoformat("2026-07-14T01:00:00-07:00")
