"""Measure each tool's definition against its def-token budget.

The budget gate is ≤1,200 tokens across all seven tools
(`docs/design/00-contract-conventions.md`). This measures the *definition a client
actually receives* — name, description, and inputSchema as serialized over MCP — not
the source code, and not an estimate.

Counted with Anthropic's `count_tokens` API rather than a generic BPE tokenizer,
because the number that matters is what the model doing tool selection actually sees.
Needs ANTHROPIC_API_KEY; run manually, not in pytest.

    uv run python scripts/measure_def_tokens.py
"""

from __future__ import annotations

import asyncio
import os
import sys

TARGETS = {
    "towerwatch_query_metrics": 220,
    "towerwatch_analyze_window": 250,
    "towerwatch_compare": 180,
    "towerwatch_query_log_events": 150,
    "towerwatch_get_monitor_status": 130,
    "towerwatch_get_runbook": 120,
    "towerwatch_run_speedtest": 150,
}
TOTAL_BUDGET = 1200
MODEL = "claude-sonnet-4-5"


async def collect_tool_defs() -> list[dict]:
    """Read the tool defs off a live server session — the same list a client sees."""
    from fastmcp import Client

    from towerwatch_ops_agent.server import build_app

    async with Client(build_app()) as client:
        tools = await client.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in tools
    ]


def count_tokens(tool_def: dict) -> int:
    """Token count for one tool def, as measured by the selecting model's tokenizer."""
    from anthropic import Anthropic

    client = Anthropic()
    response = client.messages.count_tokens(
        model=MODEL,
        messages=[{"role": "user", "content": "."}],
        tools=[tool_def],  # type: ignore[arg-type]
    )
    return response.input_tokens


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set — cannot measure.", file=sys.stderr)
        return 2

    defs = asyncio.run(collect_tool_defs())

    # Subtract the fixed overhead of an empty request so the number reported is the
    # tool def alone, not the def plus the boilerplate every call carries.
    from anthropic import Anthropic

    baseline = Anthropic().messages.count_tokens(
        model=MODEL, messages=[{"role": "user", "content": "."}]
    ).input_tokens

    print(f"{'tool':<34}{'tokens':>8}{'target':>8}{'delta':>8}")
    print("-" * 58)
    measured_total = 0
    for tool_def in defs:
        tokens = count_tokens(tool_def) - baseline
        target = TARGETS.get(tool_def["name"], 0)
        measured_total += tokens
        flag = "" if target and tokens <= target else "  OVER" if target else "  (no target)"
        print(f"{tool_def['name']:<34}{tokens:>8}{target:>8}{tokens - target:>+8}{flag}")

    print("-" * 58)
    built, total_tools = len(defs), len(TARGETS)
    print(f"{'measured total':<34}{measured_total:>8}{TOTAL_BUDGET:>8}")
    print(f"\nTokenizer: Anthropic count_tokens, model={MODEL}")
    if built < total_tools:
        print(
            f"PARTIAL: {built}/{total_tools} tools built. The ≤{TOTAL_BUDGET} gate cannot be "
            f"judged until all seven exist — this is a per-tool check only."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
