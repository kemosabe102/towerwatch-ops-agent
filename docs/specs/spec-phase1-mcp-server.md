# Phase 1 spec — TowerWatch MCP server, instrumented

Goal: a working, observable MCP server over TowerWatch's data, with defined SLIs and a cross-model cost/latency bench. This phase gates application submission and makes talk-track item 8 (MCP) fully owned — server side included.

## References (load before building)

- MCP spec: `https://modelcontextprotocol.io/sitemap.xml` → fetch relevant pages with `.md` suffix (architecture, transports, tools)
- Python SDK: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- Testing: MCP Inspector (`npx @modelcontextprotocol/inspector`)

## Tools (8–10, read-only-dominant)

Naming: `towerwatch_` prefix, action-oriented. Candidate set — finalize against what TowerWatch's data actually supports:

| Tool | Purpose | Annotations |
|---|---|---|
| `towerwatch_get_probe_status` | Current status of all 6 probe types | readOnly |
| `towerwatch_query_metrics` | Metric query with time range; **paginated** | readOnly |
| `towerwatch_analyze_window` | Summarize network quality over a window | readOnly |
| `towerwatch_compare_periods` | Compare two time windows | readOnly |
| `towerwatch_diagnose_symptom` | Map a symptom description to runbook-indexed causes | readOnly |
| `towerwatch_get_runbook` | Retrieve runbook entry by symptom/id | readOnly |
| `towerwatch_list_chaos_events` | Chaos-harness event history | readOnly |
| `towerwatch_run_probe` | Trigger a single probe on demand | idempotent, non-destructive |

Design requirements (from the MCP quality bar):
- Pydantic input schemas with constraints and an example in every field description.
- Output schemas / structured content where the SDK supports it.
- Actionable error messages: every error names what went wrong and suggests the next call.
- Pagination on anything that can return unbounded data.

## The tool-definition token budget (your specialty — make it measurable)

- Hard budget: **total tool-def payload ≤ 1,200 tokens** for the full set.
- Deliverable: a `def_tokens.md` table — tokens per tool def, total, and one paragraph on what you cut to fit and what it cost in clarity. This table feeds the S10 talk-track directly.

## Observability (day one, not retrofitted)

- One OTel span per tool call. Attributes: tool name, success/failure, duration, input size, output tokens, model (when known).
- Export into your existing Prometheus/Grafana stack.
- **SLIs defined in the README:** tool-call success rate; p50/p95 latency per tool. A Grafana dashboard renders both.

## Cross-model bench

- Fixed set of 5 tasks (drafted here, refined during build) exercising multi-tool sequences.
- Run identically through Claude + 2 other models via their tool-use APIs.
- Deliverable: `bench.md` table — per model per task: tokens in/out, wall latency, cost, task success, turns.

## Acceptance criteria (stateless gates — each independently checkable)

- [ ] All tools pass MCP Inspector interactively.
- [ ] Spans visible in Grafana for a scripted 20-call session; SLI dashboard screenshot committed.
- [ ] `def_tokens.md` exists and total ≤ budget (or documents the overage decision).
- [ ] `bench.md` exists with all cells filled.
- [ ] `CLAUDE.md` + README with architecture diagram committed.
- [ ] Stretch (non-gating): stateless streamable HTTP transport behind a flag.

## Writeup (gates phase completion)

3+ surprises, "what I'd change in production," and — per your receipts principle — for any bug found after first "done," the check that would have caught it.
