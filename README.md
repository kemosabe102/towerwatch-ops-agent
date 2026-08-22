# TowerWatch Ops Agent

An agent layer over [TowerWatch](../towerwatch) — the network-quality monitoring
project — built to demonstrate the three capabilities an enterprise agent-engineering
loop needs: **evaluation suites**, **cost/latency-aware model choice**, and **tool
retrieval**. One repo, one coherent story:

> "I took my public monitoring project and built the agent layer an enterprise would
> need around it: an instrumented MCP server with defined SLIs, an eval harness in CI
> that catches seeded regressions, a cost-aware model router, and semantic tool
> retrieval with measured selection precision."

> **At a glance**
> - **Runtime:** Python 3 + [FastMCP](https://github.com/jlowin/fastmcp), managed with [uv](https://docs.astral.sh/uv/).
> - **Domain:** TowerWatch's network-monitoring data, exposed as agent tools.
> - **Transport:** stdio first; stateless streamable HTTP as a stretch goal.
> - **Observability:** OpenTelemetry from the first tool call, into a Prometheus/Grafana stack.
> - **Tool surface:** seven tools — `query_metrics`, `analyze_window`, `compare`, `query_log_events`, `get_monitor_status`, `get_runbook`, `run_speedtest`. Contracts in [`docs/design/`](docs/design/).
> - **Status:** 🟡 **Phase 1 in progress** — the server runs and one of seven tools is built; no Phase 1 acceptance criterion is met yet. See [Status](#status).

---

## Why this project

It fills the gap between "I read about agent evaluation and routing" and "I built and
measured it." Every artifact — eval tables, benchmark numbers, precision@k charts — is
a number personally collected, not a claim from study. The domain is real data from a
project the author already owns, so the story is "I extended my own production-style
system," not "I did a tutorial."

The build runs under the author's own [Agent Collaboration Principles](docs/specs/build-plan.md#governing-standard-your-own-agent-collaboration-principles):
every phase's definition-of-done is a set of independently checkable artifacts — a
command that runs, a file that exists, a dashboard that renders. No "trust me, it works."

---

## The three phases

The project is one build in three strictly-sequenced phases. Full specs live in
[`docs/specs/`](docs/specs/); the [build plan](docs/specs/build-plan.md) is the index.
**Requirements were defined upfront in a planning process and built to as a contract** —
the specs came first, the [tool contracts](docs/design/) were derived from them, and the
[ADRs](docs/adr/) record every decision that shaped the surface.

| Phase | Ships | Spec |
|---|---|---|
| **1** | Instrumented MCP server over TowerWatch data + defined SLIs + cross-model cost/latency bench | [`spec-phase1-mcp-server.md`](docs/specs/spec-phase1-mcp-server.md) |
| **2** | Golden-set + rubric eval harness in CI that catches a seeded regression | [`spec-phase2-eval-harness.md`](docs/specs/spec-phase2-eval-harness.md) |
| **3** | Cost-aware model router + semantic tool retrieval with measured selection precision | [`spec-phase3-router-and-retrieval.md`](docs/specs/spec-phase3-router-and-retrieval.md) |
| **Cross-cutting** | Agent-facing docs, in-repo skills, ADRs, and a **measured onboarding eval** — incremental alongside the phases, never blocking | [`spec-ai-native-repo-layer.md`](docs/specs/spec-ai-native-repo-layer.md) |

**Sequence is strict:** Phase 2's evals score Phase 3's router. Don't reorder. The
cross-cutting layer is the exception — it lands incrementally and gates nothing.

---

## Repository layout

```
towerwatch-ops-agent/
├── README.md                       # this file — human-facing
├── CLAUDE.md                       # agent-facing anchor (read first if you're an agent)
├── pyproject.toml                  # PEP 621 single source of truth — deps, tooling config
├── docs/
│   ├── architecture.md             # intended shape (stub — not built yet)
│   ├── specs/                      # the governing build plan + 4 requirement specs
│   ├── design/                     # locked tool contracts (00–11) — authoritative
│   ├── adr/                        # architecture decision records
│   └── production-path.md          # personal-scale choices vs. enterprise needs
├── src/towerwatch_ops_agent/       # server, config, domain/, tools/, telemetry/
├── tests/                          # pytest suite — 95 tests
├── fixtures/stub/                  # hand-authored stub corpus (not the real one)
└── RATIONALE.md                    # deliberate choices that read as defects
```

---

## Quick start

> The server runs and serves `query_metrics`. The other six tools are not built yet.

```bash
# From repo root. uv manages the environment and lockfile.
uv sync                            # create .venv, install deps from pyproject.toml
uv run python -m towerwatch_ops_agent   # (Phase 1) launch the MCP server over stdio
```

Testing the server interactively (Phase 1) uses the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv run python -m towerwatch_ops_agent
```

---

## Status

🟡 **Phase 1 in progress.** The MCP server runs over stdio and serves
`query_metrics` end to end against a fixture. **None of Phase 1's five acceptance
criteria are met yet** — see [`spec-phase1-mcp-server.md`](docs/specs/spec-phase1-mcp-server.md)
for the gate list.

**Built and running:**

- [x] Directory skeleton, `pyproject.toml`, `.gitignore`, MIT license
- [x] README, `CLAUDE.md` (with binding invariants), architecture stub
- [x] The build plan and all four requirement specs in [`docs/specs/`](docs/specs/)
- [x] **Locked tool contracts** — [`docs/design/`](docs/design/) 00–11: conventions, seven
      tool docs, skills interfaces, span schema, fixture manifest, eval design
- [x] **ADRs** — [`docs/adr/`](docs/adr/), the decisions behind the tool surface
- [x] **MCP server + composition root** — `server.py`, `config.py`, stdio transport
- [x] **`query_metrics`** — 1 of 7 tools, with the `data_status` envelope enforced
- [x] **`FixtureClient` + manifest loader** — ADR-0002's dual-mode seam, fixture side only
- [x] **Span instrumentation** — one span per tool call, secrets structurally excluded
- [x] **CI workflow** — ruff, format, pyright, pytest on every PR branch head
- [x] `RATIONALE.md` — deliberate choices a reviewer would otherwise report as defects

**Deferred** (not yet built — see `CLAUDE.md` for the phase gates):

- [ ] **Six remaining tools** — `analyze_window`, `compare`, `query_log_events`,
      `get_monitor_status`, `get_runbook`, `run_speedtest`
- [ ] **`GrafanaCloudClient`** — the live half of the `DataClient` Protocol
- [ ] **Curated fixture corpus** — `fixtures/stub/` is a two-window hand-authored stub
      proving the format only, not the real deterministic corpus
- [ ] **OTel exporter + SLI dashboard** — spans are emitted but go nowhere; no
      `MeterProvider`, so no duration histograms
- [ ] `def_tokens.md` — the tool-def token budget measurement (script exists, never run)
- [ ] `bench.md` — cross-model cost/latency bench
- [ ] Phase 2 — eval harness + CI + seeded-regression showpiece
- [ ] Phase 3 — model router + semantic tool retrieval
- [ ] In-repo skills under `.claude/skills/` — `diagnose-rca`, `evidence-pack`, plus the
      golden-path skills (`add-tool`, `run-evals`) created when first walked manually
- [ ] Measured onboarding eval (`docs/onboarding-eval.md`) — first run after Phase 1

---

## For AI assistants

If you're an agent working in this repo, read **[`CLAUDE.md`](CLAUDE.md)** first. It
carries the phase sequence, the stateless-gates working standard, and an explicit map of
what exists versus what is still a stub, so you don't reason about code that isn't there
yet. `RATIONALE.md` records the deliberate choices that read as defects on sight — read it
before reporting one.
