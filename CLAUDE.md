# CLAUDE.md

> **Budget: 110 lines / ~1,500 tokens** (limit: 150 lines, per
> [`spec-ai-native-repo-layer.md`](docs/specs/spec-ai-native-repo-layer.md)). Measured
> 2026-07-25. Deep context lives in `docs/` and loads on demand — this file stays a map,
> never a manual. Re-measure when you edit it.

Agent-facing guide. The user-facing README is imported below and is the source of truth
for the project story, the three-phase map, and the toolchain — read it first, then come
back here for the agent-only notes.

@README.md

---

## Repo state — read before reasoning about code

**There is no implementation yet.** `src/` and `tests/` contain package markers only. Do
not reference, import, or assume the existence of any tool, module, function, or eval that
the specs describe as *to be built* — none of it exists on disk yet.

**What does exist is the contract layer.** When asked to build, work from
[`docs/design/`](docs/design/) (the locked tool contracts) and [`docs/adr/`](docs/adr/)
(the decisions behind them) — not from memory of "what the code probably does," and not
from the Phase 1 spec's candidate tool table, which `docs/design/` supersedes.

The README's [Status](README.md#status) section is the authoritative present-vs-deferred
list. Keep it in sync when you land work.

## Binding invariants — these post-date the original specs

Non-negotiable, and they constrain every tool. They came out of the design sessions, so
the older spec text does not always reflect them:

- **No LLM calls inside the MCP server.** The server interprets only against *enumerable*
  context — deterministic aggregation, thresholds, reference frames, budget math.
  Open-context interpretation (symptom narratives, cross-signal attribution) belongs to
  the client model.
- **Secrets never appear in tool schemas, results, logs, or span attributes.** *The agent
  holds intent; the server holds privilege.*
- **Every tool response carries `data_status`**, distinguishing the three absences:
  `empty_window` (collected here, nothing in range — a true negative) vs. `not_collected`
  (this site doesn't collect it — **no evidence, do not infer health**) vs. `error`. Plus
  `ok` and `partial`. Never let a model read absence as health.
- **Data access is dual-mode behind a Protocol** — `GrafanaCloudClient` (live) and
  `FixtureClient` (curated, committed). Tests and evals run against the fixture only, for
  determinism.
- **The tool surface is exactly seven tools:** `query_metrics`, `analyze_window`,
  `compare`, `query_log_events`, `get_monitor_status`, `get_runbook`, `run_speedtest`.
  Skills (`diagnose-rca`, `evidence-pack`) are procedures composed over these tools, not
  tools themselves.
- **Derive, don't hardcode:** the runbook section enum, the site enum, and the log event
  types are all derived at server startup from their sources, so definitions cannot drift
  stale.

## Phase sequence — strict, do not reorder

The build is three phases (see [`docs/specs/build-plan.md`](docs/specs/build-plan.md)):

1. **Phase 1** — instrumented MCP server + SLIs + cross-model bench. *Gates everything.*
2. **Phase 2** — eval harness in CI + seeded-regression catch.
3. **Phase 3** — cost-aware router + semantic tool retrieval.

**Phase 2's golden set is the judge that scores Phase 3's router.** Building Phase 3
before Phase 2 leaves the router with nothing to measure it against. Never reorder.

## Governing standard — stateless gates

Every phase's definition-of-done is a set of independently checkable artifacts, per the
author's [Agent Collaboration Principles](docs/specs/build-plan.md#governing-standard-your-own-agent-collaboration-principles):

- **Stateless gates:** each acceptance criterion is a command that runs, a file that
  exists, or a dashboard that renders — never "trust me, it works." A clean prior phase
  does not waive a later gate.
- **Checkability-by-design:** outputs are tables, eval results, and traces — not
  narratives. If a claim can't be checked from an artifact, it isn't done.
- **Receipts:** for every bug found after a first "done," name the check that caught it
  (or the check that *should* have, and add it).

Each phase spec has an **Acceptance criteria** section — those checkboxes are the gates.
Do not declare a phase complete until each is independently verifiable.

## Toolchain conventions

- **Environment:** [uv](https://docs.astral.sh/uv/). `uv sync` to set up, `uv run …` to
  execute. `pyproject.toml` (PEP 621) is the single source of truth for deps and tooling
  config — mirror the parent [`towerwatch`](../towerwatch) repo's convention.
- **Server:** Python + [FastMCP](https://github.com/jlowin/fastmcp). stdio transport
  first; stateless streamable HTTP is a Phase 1 *stretch*, not a gate.
- **Schemas:** Pydantic models with constraints and an example in every field
  description (Phase 1 requirement).
- **Lint/type/test:** ruff + pyright + pytest, matching the parent repo. A CI workflow
  is deferred until Phase 1 has code to lint.

## Relationship to the towerwatch repo

This project layers an agent surface over the sibling [`towerwatch`](../towerwatch)
repo's real network-monitoring data. Treat towerwatch as the **domain source of truth**:
its data model, probe types, and runbook define what the MCP tools can honestly expose.
When Phase 1 tool design needs to know what data exists, read towerwatch's
`docs/architecture.md`, `docs/metrics-inventory.md`, and `docs/runbook.md` — do not
invent metrics TowerWatch doesn't collect.

## Scope discipline — the failure mode to avoid

Scope creep is the failure mode of portfolio projects. The specs' out-of-scope list is
binding: **no UI, no LangGraph, no multi-user auth, no doc-RAG beyond the runbook
side-quest, no Kubernetes.** The acceptance criteria are the whole job. If a change isn't
serving a named acceptance criterion, it's probably creep — flag it as an explicit choice
rather than smuggling it in.
