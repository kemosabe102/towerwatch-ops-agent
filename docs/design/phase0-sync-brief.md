# Phase 0 sync brief — bringing the scaffold in line with the design sessions

**Context for the coding agent:** the scaffold was built from the original specs, before the design sessions that produced Phase 0's decisions. This brief is the delta. Where it conflicts with the Phase 1 spec's candidate tool table, **this brief and `docs/design/` win** — the spec is the inbound requirement; the design docs are the derived, current contract.

## Already fixed directly (committed alongside this brief)

- `docs/specs/build-plan.md` **replaced** — the repo had the older version, missing the "Cross-cutting layer" paragraph that references the repo-layer spec.
- `docs/specs/spec-ai-native-repo-layer.md` **added** — the fifth requirements doc; it was missing from the set.

## The 8 locked decisions (each becomes an ADR in `docs/adr/`)

1. Separate repo (`towerwatch-ops-agent`); TowerWatch untouched.
2. **Dual-mode data access:** Protocol adapter, two impls — live Grafana Cloud + committed curated fixture. Fixture is authoritative for tests/evals (determinism); live for demo/real use.
3. `run_probe` cut — analytical system, 60 s loop suffices.
4. **Budget: one source, three surfaces** — computed in server code; guard inside `run_speedtest`, pace in `get_monitor_status`, actionable refusal message.
5. `run_speedtest` returns server-composed before/after context (pre snapshot + concurrent radio metrics).
6. Runbook access is keyed lookup, **not RAG** (Phase 3 measures retrieval against the load-the-whole-doc baseline).
7. `get_runbook` section enum **derived from the doc's headings at server startup** (living document; def can't drift).
8. `diagnose_symptom` cut as a tool → **skill `diagnose-rca`** (procedure, not capability; the model does symptom→section matching natively over the enum).

## Final tool surface — 7 tools (supersedes the spec's candidate table)

`query_metrics` · `analyze_window` · `compare` · `query_log_events` · `get_monitor_status` · `get_runbook` · `run_speedtest`

Renames from spec candidates: `list_chaos_events` → `query_log_events` (source-explicit) · `get_probe_status` → `get_monitor_status` (whose status: the monitor, not the network) · `compare_periods` → `compare` (adds cross-host dimension). Added: `run_speedtest`. Cut: `run_probe`. Converted: `diagnose_symptom` → skill. Full contracts: `docs/design/00–09` (pending Anthony's review before landing).

## Edits needed — README.md

- Phase table: add the **cross-cutting repo-layer** row (agent-facing docs, in-repo skills, measured onboarding eval — incremental alongside phases, never blocking; per `spec-ai-native-repo-layer.md`).
- Status section: add repo-layer items. **ADRs are day-one, not deferred** — the repo-layer spec says root CLAUDE.md + first ADRs ship on day one of Phase 1; 8 decisions are ADR-ready above.
- One provenance line where the specs are introduced: *"Requirements were defined upfront in a planning process and built to as a contract."*

## Edits needed — CLAUDE.md

Add a **binding invariants** section (these exist now; the scaffold predates them):

- No LLM calls inside the MCP server — server interprets only against enumerable context (deterministic aggregation, reference frames, budget math); open-context interpretation belongs to the client model.
- Secrets never appear in tool schemas, results, or context — *the agent holds intent; the server holds privilege.*
- Every tool response carries `data_status` distinguishing three absences: `not_collected` / `empty_window` / `error` — never let a model read absence as health.
- Data access is dual-mode behind a Protocol; tests and evals run against the fixture only.
- Tool surface is the 7 above; `docs/design/` is authoritative over the Phase 1 spec's candidate list.

## Edits needed — docs/architecture.md

- `domain/`: state dual-mode explicitly (GrafanaCloudClient | FixtureClient behind a Protocol — continues TowerWatch's Protocol/hand-fakes testing philosophy).
- Data-flow diagram: "chaos events" → "log events + annotations"; add the fixture path beside the live path.
- Add: skills live in `.claude/skills/` (`diagnose-rca`, `evidence-pack`) — procedures composed over the tools, not tools.
- Point to `docs/design/` for tool contracts and `docs/adr/` for decisions.

## New directories

- `docs/adr/` — create now; populate from the 8 decisions (nearly free while fresh).
- `docs/design/` — contract docs 00–09 land here after review.

## New requirements not in any spec (from design sessions)

- **Sparse coverage is first-class:** phone host lacks Pi metric groups; hardware metrics not at all sites → per-site coverage reported by `get_monitor_status`; `compare` returns comparable intersection + names non-comparables.
- **Multi-connection-type reference frames** in `analyze_window`: `self_baseline` / `type_profile` / `anchored_trend` (slow-drift catch).
- **`docs/production-path.md`** (stub now, grows per phase): personal-scale choices vs enterprise needs — MCP gateway/always-on, auth/multi-tenancy, pgvector, online sampling/drift, alert-triggered investigation.
- **Loop-safety conventions** (see `00-contract-conventions.md`): actionable errors with `retryable` flags; max 2 retries; repeated identical error = stop signal; MCP-unreachable = report and stop, never loop.
