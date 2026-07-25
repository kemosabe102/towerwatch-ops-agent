# Agent portfolio build plan — one project, three phases

Purpose: fill both resume placeholder slots, convert talk-track items from transfer/study tier to owned, and generate the "here's what surprised me" data points that separate lived experience from reading. Target role: Zapier Staff Engineer, Applied AI (Agents) — but every artifact generalizes to any agent-engineering loop.

## The project: TowerWatch Ops Agent

An MCP server exposing TowerWatch's network-monitoring domain as agent tools, wrapped in the three capabilities the Zapier JD names: evaluation suites, cost/latency-aware model choice, and tool retrieval. One repo, one coherent story:

> "I took my public monitoring project and built the agent layer an enterprise would need around it: an instrumented MCP server with defined SLIs, an eval harness in CI that catches seeded regressions, a cost-aware model router, and semantic tool retrieval with measured selection precision."

**Why TowerWatch as the domain (recommended):** real data you own, public repo, zero employer IP risk, and the demo composes with an existing portfolio piece — the story becomes "I extended my own production-style system," not "I did a tutorial." **Alternative:** a synthetic incident-ops domain (fake FireHydrant-style data) — closer to your day-job vocabulary, but requires fabricating data and can't be shown running live. Trade-off: TowerWatch wins on authenticity and demo-ability; take the alternative only if TowerWatch's data model turns out too thin for interesting multi-tool questions (check during Phase 1 tool design).

## Governing standard: your own Agent Collaboration Principles

The build runs under your published framework — and that fact is itself interview material ("I audit my own projects with the standard I wrote"):

- **Stateless gates:** every phase's definition-of-done is a set of independently checkable artifacts — a command that runs, a file that exists, a dashboard that renders. No "trust me, it works."
- **Checkability-by-design:** outputs are tables, eval results, and traces — not narratives.
- **Receipts:** each phase's writeup names, for every issue found, the check that caught it (or should have).

## Tech decisions (made once, here)

| Decision | Choice | Trade-off accepted |
|---|---|---|
| Language | **Python + FastMCP** | The MCP ecosystem's reference guidance leans TypeScript; Python wins here because it's Zapier's language and your coding-reps track — the build doubles as interview-fluency practice |
| Transport | stdio first; stateless streamable HTTP as a stretch goal | Remote transport is a Phase 1 stretch, not a gate |
| Schemas | Pydantic models, constraints + examples in every field description | — |
| Observability | OpenTelemetry from the first tool call — into your existing Prometheus/Grafana stack | — |
| Vector store (Phase 3) | Chroma or sqlite-vec (zero-infra) | pgvector is the production answer; say so in the writeup, don't build it |
| Models | Claude (primary) + 2 of: GPT, Gemini, a small-tier model for routing | — |

## Phase map

| Phase | Spec | Ships | Converts (talk-track) | Timebox |
|---|---|---|---|---|
| 1 | `spec-phase1-mcp-server.md` | Instrumented MCP server + SLIs + cross-model bench | 8 → fully owned; 13, 16 partial | ~1 week part-time. **Gates application submission.** |
| 2 | `spec-phase2-eval-harness.md` | Golden set + rubric evals in CI, seeded-regression catch | 20; deepens 1–2 | ~3–4 days |
| 3 | `spec-phase3-router-and-retrieval.md` | Cost-aware router + semantic tool retrieval with precision evals | 16 complete, 18 | ~1 week |

Sequence is strict: Phase 2's evals score Phase 3's router; don't reorder. Total ~3 weeks part-time → shipping mid-August, inside the Aug–Sept application window.

**Cross-cutting layer — `spec-ai-native-repo-layer.md`:** the repo doubles as an AI-native developer-onboarding showcase (agent-facing docs, in-repo skills, primary/sub-agent/reviewer hooks, and a *measured* onboarding eval). Built incrementally alongside the phases — 2–4 days total, never blocking. Phase 1 still gates submission.

## Interview-artifact requirements (every phase)

1. A metrics table (specified per phase) — numbers you personally collected.
2. A short writeup: **minimum 3 surprises**, plus "what I'd change in production." The surprises are the point; they can't be faked by study.
3. Repo hygiene: `CLAUDE.md` with your agent-facing conventions (this is itself a portfolio artifact), README with an architecture diagram, honest scope notes.

## Out of scope — do not build

No UI. No LangGraph dependency (Phase 3 retrieval ≠ a framework tour). No multi-user auth. No doc-RAG beyond the runbook-chunking side-quest in Phase 3. No Kubernetes deployment (a compose file is plenty). Scope creep is the failure mode of portfolio projects; the specs' acceptance criteria are the whole job.

## Resume placeholder mapping

- Placeholder 1 (MCP server) ← Phase 1 ships → 2–3 line description + repo link.
- Placeholder 2 (tool-retrieval build) ← Phase 3 ships → framed in Zapier vocabulary: intent→action selection precision.
