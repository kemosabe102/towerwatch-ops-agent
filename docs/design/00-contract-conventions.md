# Contract conventions — cross-cutting rules for every tool

All tool contracts inherit these rules. Individual tool docs state only their specifics.

## Naming

- Prefix: `towerwatch_`. Pattern: `verb_object`, named for **what the caller gets, not the activity** (rename rationale: a def is a prompt; the name drives selection).
- Source-explicit where ambiguity is possible: `query_log_events` (Loki), not `query_events`.
- Renames from spec candidates: `list_chaos_events` → `query_log_events` · `get_probe_status` → `get_monitor_status` (status of the *monitor*, not the network — the network's status is `analyze_window`'s job).

## Selection sentence (required per tool)

Every tool doc contains one sentence: *"The model picks me over my neighbors when ___."* If the sentence can't be written without overlapping another tool's, the surface is wrong — fix the surface, not the description.

## Response envelope (every tool)

Every response carries a `data_status` field distinguishing the **three absences** (never let the model confuse them):

| data_status | Meaning | Model's correct reading |
|---|---|---|
| `ok` | Data present | proceed |
| `empty_window` | Collected at this site, nothing in range | true negative — absence of events IS evidence |
| `not_collected` | Site doesn't collect this metric group | **no evidence — do not infer health** |
| `partial` | Some requested groups present, others not | reason only over what's present; `coverage_notes` lists gaps |
| `error` | Query failed | see error contract; retry rules apply |

`not_collected` and `empty_window` are the load-bearing distinction (grounding-failure prevention).

## Error contract (actionable, loop-safe)

Every error names: **what went wrong · why · the suggested next call · `retryable: true/false`** (+ `retry_after_s` when rate-limited).

Loop-safety: **rails, not machinery** (scaffolding is model-relative — current frontier models rarely loop; the rails exist for the smaller tiers the Phase 3 router will send here, and get revisited per routed model):
- Guidance level (agent instructions / skill text): retry only on `retryable: true`; a repeated *identical* error is a stop signal — report what's known, suggest the manual path; MCP server unreachable → report and stop.
- Hard limits only where cost is real, and those live server-side (the speedtest rate/budget guards) — never rely on model discipline for money.
- Skills keep per-gate attempt caps and "insufficient evidence" as a legal exit — cheap to state, they define done-ness as much as safety.

## Pagination

Any tool that can return unbounded data paginates: `page_size` (default small), `next_page_token`. Responses state `truncated: true` explicitly — silent truncation is failure class #4.

## Units, time, sites

- Units in field names (`_ms`, `_mbps`, `_bytes`, `_c`) — matches TowerWatch's `_ms` convention.
- Time: ISO-8601 with explicit offset; eval questions pin windows (Phase 2 stability rule).
- `site` is an enum derived from configured sites at server startup (currently `standstill`, `home`) — same derive-don't-hardcode rule as the runbook keys.

### The clock seam (`fixture_now`)

"Now" is resolved through one seam with two sources: the system clock in live mode, and a
frozen `fixture_now` timestamp read from the fixture manifest at startup in fixture mode
(same derive-at-startup rule as the `site` enum — see [ADR-0007](../adr/0007-derive-enums-at-server-startup.md)
and [`10-fixture-manifest.md`](10-fixture-manifest.md)).

- **Not a tool parameter.** No def-token cost, no schema change, and no tool learns which
  mode it is in — this preserves the core property of [ADR-0002](../adr/0002-dual-mode-data-access-via-protocol.md).
- **Relative-window handling is identical in both modes.** Fixture mode must exercise the
  default resolution path, not bypass it. A fixture that cannot run the default path
  leaves the most-used production behavior untested — which is the divergence dual-mode
  testing exists to prevent.
- Absolute windows are unaffected: eval questions still pin them (stability rule above).
  The seam matters for any input that resolves against "now."

## Annotations

All tools `readOnly` except `run_speedtest` (non-read-only → host approval gate). Nothing is destructive.

## Def-token budget (gate: ≤ 1,200 total, per Phase 1 spec)

Allocation targets (soft per tool, hard in total) — measured in `def_tokens.md`, wording iterated until the *selection sentence survives compression*:

| Tool | Target |
|---|---|
| query_metrics | 220 |
| analyze_window | 250 |
| compare | 180 |
| query_log_events | 150 |
| get_monitor_status | 130 |
| get_runbook | 120 |
| run_speedtest | 150 |
| **Total** | **1,200** |

Note: current provider guidance on per-def length should be verified at build time (numbers-card refresh), not recalled — the binding constraint here is the spec's total.

## Determinism placement (the standing rule)

Server code interprets against enumerable context (arithmetic, aggregation, thresholds, reference frames, budget math). The model interprets against open context (symptom narratives, cross-signal attribution, which frame answers the user). No LLM calls inside the server.
