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
> - **Status:** 🟡 **Contracts locked, implementation not started** — requirements, tool contracts, and decisions are committed; no code yet. See [Status](#status).

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
│   ├── design/                     # locked tool contracts (00–09) — authoritative
│   ├── adr/                        # architecture decision records
│   └── production-path.md          # personal-scale choices vs. enterprise needs
├── src/towerwatch_ops_agent/       # package (marker only this pass)
└── tests/                          # pytest suite (marker only this pass)
```

---

## Quick start

> Nothing runs yet — this is a scaffold. These are the intended mechanics once Phase 1
> lands, recorded here so the toolchain is unambiguous.

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

🟡 **Contracts locked, implementation not started.** Requirements, tool contracts, and
decisions are complete and committed; no code has been written yet. Present:

- [x] Directory skeleton, `pyproject.toml`, `.gitignore`, MIT license
- [x] README, `CLAUDE.md` (with binding invariants), architecture stub
- [x] The build plan and all four requirement specs in [`docs/specs/`](docs/specs/)
- [x] **Locked tool contracts** — [`docs/design/`](docs/design/) 00–09: conventions, seven
      tool docs, skills interfaces, span schema
- [x] **ADRs** — [`docs/adr/`](docs/adr/), the decisions behind the tool surface
- [x] PR template requesting verification receipts

**Deferred** (not yet built — see `CLAUDE.md` for the phase gates):

- [ ] Phase 1 — MCP server, tools, SLIs, cross-model bench
- [ ] Phase 2 — eval harness + CI + seeded-regression showpiece
- [ ] Phase 3 — model router + semantic tool retrieval
- [ ] Curated fixture corpus — the deterministic data behind tests and evals
- [ ] In-repo skills under `.claude/skills/` — `diagnose-rca`, `evidence-pack`, plus the
      golden-path skills (`add-tool`, `run-evals`) created when first walked manually
- [ ] Measured onboarding eval (`docs/onboarding-eval.md`) — first run after Phase 1
- [ ] `def_tokens.md` — the tool-def token budget measurement (lands with Phase 1)
- [ ] CI workflow (`.github/workflows/`) — lands with Phase 1, when there's code to lint

---

## For AI assistants

If you're an agent working in this repo, read **[`CLAUDE.md`](CLAUDE.md)** first. It
carries the phase sequence, the stateless-gates working standard, and — important while
the repo is a scaffold — an explicit map of what exists versus what is still a stub, so
you don't reason about code that isn't there yet.
