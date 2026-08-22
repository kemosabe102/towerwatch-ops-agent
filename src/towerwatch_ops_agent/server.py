"""The composition root: build the client, derive the enums, register the tools.

Everything mode-specific is decided here, once. Tools receive a `DataClient` and never
learn which implementation they got (ADR-0002).
"""

from __future__ import annotations

import logging
from enum import Enum

from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations

from towerwatch_ops_agent.config import MODE_FIXTURE, ServerConfig
from towerwatch_ops_agent.domain.fixture_client import FixtureClient
from towerwatch_ops_agent.domain.models import build_site_enum
from towerwatch_ops_agent.domain.protocol import DataClient
from towerwatch_ops_agent.tools.query_metrics import (
    TOOL_DESCRIPTION,
    TOOL_NAME,
    QueryMetricsResponse,
    build_request_model,
    query_metrics,
)

logger = logging.getLogger(__name__)


def build_client(config: ServerConfig) -> tuple[DataClient, list[str]]:
    """Construct the data client for the configured mode, plus its site list."""
    if config.mode != MODE_FIXTURE:
        raise NotImplementedError(
            "Live mode needs GrafanaCloudClient, which is not built yet. "
            "Run with TOWERWATCH_MODE=fixture."
        )
    client = FixtureClient(config.fixture_manifest)
    return client, client.sites


def build_app(config: ServerConfig | None = None) -> FastMCP:
    resolved = config or ServerConfig.from_env()
    client, sites = build_client(resolved)
    site_enum: type[Enum] = build_site_enum(sites)
    mode = resolved.mode

    # ADR-0007's observability requirement: a silently-empty derived enum must be
    # visible at startup rather than presenting as an empty dropdown later.
    logger.info(
        "Derived enums at startup: sites=%s (mode=%s)",
        sorted(s.value for s in site_enum),
        mode,
    )

    app = FastMCP(name="towerwatch-ops-agent")
    request_model = build_request_model(site_enum)

    def towerwatch_query_metrics(request) -> QueryMetricsResponse:
        return query_metrics(request, client=client, mode=mode)

    # Set the annotation as a live object rather than in the signature: this module
    # uses `from __future__ import annotations`, so a written annotation would be the
    # string "request_model", which FastMCP cannot resolve — `request_model` is a local
    # built at startup from the derived site enum, not a module-level name.
    towerwatch_query_metrics.__annotations__["request"] = request_model

    app.add_tool(
        Tool.from_function(
            towerwatch_query_metrics,
            name=TOOL_NAME,
            description=TOOL_DESCRIPTION,
            # Read-only per conventions; only run_speedtest is non-read-only.
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        )
    )
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_app().run()
