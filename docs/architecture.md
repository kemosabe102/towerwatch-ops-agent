# Architecture

> **Status: intended shape, not built.** This document describes where the pieces are
> meant to go once the phases are implemented. Nothing here exists in `src/` yet — see
> the [README status](../README.md#status) for what's actually present. Written now so
> the target is unambiguous before any code lands.

## The shape in one paragraph

An MCP server (FastMCP, stdio) exposes TowerWatch's network-monitoring domain as a small
set of read-only-dominant tools. Every tool call emits an OpenTelemetry span from day
one, feeding SLIs (success rate, p50/p95 latency) into a Prometheus/Grafana stack. On top
of the server sit two later layers: an eval harness (golden set + rubric, run in CI) that
scores tool behaviour, and a cost-aware model router plus semantic tool-retrieval index
that the eval harness measures.

## Intended module layout

Populated as phases land. The parenthetical marks which phase introduces each piece.

```
src/towerwatch_ops_agent/
├── __init__.py
├── __main__.py          # (P1) stdio entry point → serves the MCP tools
├── server.py            # (P1) FastMCP app; registers tools
├── tools/               # (P1) one module per towerwatch_* tool, Pydantic schemas
├── domain/              # (P1) dual-mode data access behind a Protocol:
│                        #      GrafanaCloudClient (live) | FixtureClient (curated)
├── telemetry/           # (P1) OTel span wrapper; SLI attributes
├── eval/                # (P2) golden set, rubric scorer, CI harness
├── router/              # (P3) small-first / escalate-on-failure model router
└── retrieval/           # (P3) tool-def embedding index + intent→action selection
```

**Skills are not in `src/`.** `diagnose-rca` and `evidence-pack` live in
`.claude/skills/` — they are *procedures* composed over the tools (how to proceed), not
*capabilities* the model lacks (what the tools provide). See
[`design/08-skills-interfaces.md`](design/08-skills-interfaces.md).

## Data flow (Phase 1)

```
MCP client (Claude / Inspector)
        │  tool call (stdio, JSON-RPC)
        ▼
   FastMCP server  ──emits──►  OTel span (tool, success, duration, data_status,
        │                       │          mode=live|fixture, site, model)
        │  reads                ▼
        │              Prometheus / Grafana (SLIs)
        ▼
   Data access Protocol
        ├── GrafanaCloudClient ──► TowerWatch live data
        │     (live: demo, real use)   (Prometheus metrics, Loki log events,
        │                               Grafana annotations, runbook)
        └── FixtureClient ────────► committed curated fixture
              (authoritative for tests + evals — determinism)
```

The `mode` span attribute keeps live and fixture traffic separable; they are never mixed
in a dashboard.

## Why these boundaries

Each layer has one job and a checkable output, so it can be understood and tested
independently:

- **`tools/` + `domain/`** — the server surface. Checkable via MCP Inspector and the
  tool-def token budget table.
- **`telemetry/`** — observability. Checkable via spans visible in Grafana for a scripted
  session.
- **`eval/`** — correctness gate. Checkable via a CI run that fails on a seeded regression.
- **`router/` + `retrieval/`** — the cost/latency and selection-precision story. Checkable
  via the router comparison table and precision@k numbers.

## Where to read next

This file is the map. The territory:

| You want | Read |
|---|---|
| What each tool accepts and returns | [`design/`](design/) — 00 conventions, 01–07 one per tool |
| Why the surface looks like this | [`adr/`](adr/) — the decisions, with alternatives weighed |
| What each phase must ship | [`specs/`](specs/) — the upfront requirements |
| What the skills do | [`design/08-skills-interfaces.md`](design/08-skills-interfaces.md) |
| The span schema | [`design/09-observability-spans.md`](design/09-observability-spans.md) |
| Personal-scale vs. enterprise trade-offs | [`production-path.md`](production-path.md) |

Where `design/` and the phase specs disagree, **`design/` wins** — the specs are the
inbound requirement, the design docs are the derived, current contract.
