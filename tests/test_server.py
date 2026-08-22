"""End-to-end over a real MCP client session — the registration path Inspector uses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from towerwatch_ops_agent.config import MODE_FIXTURE, ServerConfig
from towerwatch_ops_agent.server import build_app
from towerwatch_ops_agent.tools.query_metrics import TOOL_NAME


@pytest.fixture
def app(stub_manifest_path: Path):
    return build_app(ServerConfig(mode=MODE_FIXTURE, fixture_manifest=stub_manifest_path))


async def _call(client: Client, **params) -> dict:
    result = await client.call_tool(TOOL_NAME, {"request": params})
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.asyncio
async def test_tool_is_listed_as_read_only(app) -> None:
    async with Client(app) as client:
        tools = await client.list_tools()
    assert [t.name for t in tools] == [TOOL_NAME]
    assert tools[0].annotations is not None
    assert tools[0].annotations.readOnlyHint is True


@pytest.mark.asyncio
async def test_site_enum_is_derived_into_the_schema(app) -> None:
    """The schema advertises exactly the configured sites — never a hardcoded list."""
    async with Client(app) as client:
        tools = await client.list_tools()
    schema = json.dumps(tools[0].inputSchema)
    assert "standstill" in schema
    assert "home" in schema
    assert "atlantis" not in schema


@pytest.mark.asyncio
async def test_three_acceptance_calls(app) -> None:
    """The slice-one gate: ok, not_collected, and empty_window over a live session."""
    window = {"start": "2026-07-14T00:00:00-07:00", "end": "2026-07-14T01:00:00-07:00"}
    async with Client(app) as client:
        ok = await _call(client, site="standstill", metric_group="latency", **window)
        absent = await _call(client, site="home", metric_group="signal", **window)
        empty = await _call(
            client,
            site="standstill",
            metric_group="latency",
            start="2026-07-14T02:00:00-07:00",
            end="2026-07-14T03:00:00-07:00",
        )

    assert ok["data_status"] == "ok"
    assert ok["series"]["rtt_avg_google"]
    assert absent["data_status"] == "not_collected"
    assert empty["data_status"] == "empty_window"
    assert absent["data_status"] != empty["data_status"]


@pytest.mark.asyncio
async def test_live_mode_fails_loudly_until_the_client_exists(stub_manifest_path: Path) -> None:
    """Better a refused startup than a server that silently serves fixture data as live."""
    with pytest.raises(NotImplementedError):
        build_app(ServerConfig(mode="live", fixture_manifest=stub_manifest_path))
