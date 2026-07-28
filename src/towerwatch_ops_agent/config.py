"""Startup configuration: which data mode, and where the fixture lives.

Kept separate from `server.py` so the composition root stays a thin wiring step.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_MANIFEST = REPO_ROOT / "fixtures" / "stub" / "manifest.yaml"

MODE_FIXTURE = "fixture"
MODE_LIVE = "live"


@dataclass(frozen=True)
class ServerConfig:
    mode: str
    fixture_manifest: Path

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Read config from the environment.

        Defaults to fixture mode: live mode needs a `GrafanaCloudClient` that does not
        exist yet, so defaulting to live would fail at startup rather than serve.
        """
        mode = os.environ.get("TOWERWATCH_MODE", MODE_FIXTURE).strip().lower()
        if mode not in (MODE_FIXTURE, MODE_LIVE):
            raise ValueError(
                f"TOWERWATCH_MODE must be {MODE_FIXTURE!r} or {MODE_LIVE!r}, got {mode!r}"
            )
        manifest = Path(
            os.environ.get("TOWERWATCH_FIXTURE_MANIFEST", str(DEFAULT_FIXTURE_MANIFEST))
        )
        return cls(mode=mode, fixture_manifest=manifest)
