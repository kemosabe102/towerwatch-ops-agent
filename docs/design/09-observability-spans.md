# Observability contract — spans, SLIs, and the analysis playbook (v2)

Decided once, now — Phase 3's router table reads these spans; the schema must not change mid-build. Philosophy per Anthony's review: **capture the core raw signals wide, slice later.** Spans are the raw record (every call is an event with full attributes); aggregates and views are derived downstream — so an analysis question we haven't thought of yet is still answerable from data we did collect. Outliers are first-class: max and p99 are kept everywhere, because tails are where network problems and agent pathologies both live.

## Span: one per tool call

`towerwatch.tool_call`, emitted by server middleware (one implementation, uniform attributes — agent-authored tools inherit instrumentation for free).

| Attribute | Type | Notes |
|---|---|---|
| `tool.name` | str | the towerwatch_* name |
| `tool.success` | bool | error responses = false |
| `tool.error_type` | str? | machine class (`budget_exceeded`, `unknown_metric`, …) |
| `tool.duration_ms` | int | wall time |
| `tool.data_status` | str | envelope value — three-absences observable in aggregate |
| `tool.input_bytes` / `tool.output_bytes` | int | payload sizes; output_bytes is what lands in model context |
| `tool.output_tokens_est` | int | bytes/4 heuristic, labeled estimate |
| `tool.page_index` | int? | pagination depth on paged calls (deep paging = payload-design smell) |
| `tool.retry` | bool | same tool re-called after an error in this task — loop telemetry |
| `site` | str? | when site-targeted |
| `mode` | str | `live` \| `fixture` — never mixed in dashboards |
| `task.id` / `session.id` | str? | correlation — sequences and per-task rollups come from these |
| `model` | str? | when known (harness always passes it; interactive may not) |

Harness-side (bench, Phase 2/3) parent span per task: `task.id`, `model`, true `tokens_in/out` from the API, `cost_usd`, `turns`, task success. Router metrics derive from parents; per-tool truth from children.

## SLIs (README-defined, Grafana-rendered)

Durations as **histograms with explicit buckets** so p50/p95/**p99** are derivable per tool per site; **max** tracked exactly from span records (spans are events — the p100 is never lost to bucketing).

- Tool-call success rate (overall, per tool, per error_type)
- p50 / p95 / p99 / max duration per tool (analyze_window and run_speedtest on their own panels)
- `data_status` mix per tool — rising `not_collected`/`partial` = coverage regression; rising `empty_window` on a tool that shouldn't see it = query-shaping problem
- Output tokens per call per tool — the context-economics SLI; regression here taxes every future turn silently
- Retry rate per tool and per error_type — the loop-rails effectiveness measure

## The analysis playbook — what this data answers (and how)

- **Bottlenecks:** which tool dominates task wall-time? Compare per-tool p99 against per-task duration from parent spans; a task-latency problem is almost always one tool's tail, not everything being slow.
- **Sequence mining:** frequent tool-call n-grams from `task.id`-correlated traces. A recurring 3-call sequence is a composition candidate (skill, or server-side like the speedtest pre/post block); an unusually *long* chain per task signals a missing capability or a def that isn't guiding selection.
- **Waste and def quality:** `unknown_metric`/`unknown_section` error rates = vocabulary problems in defs; high `empty_window` = the model queries wrong windows (def examples needed); retry clusters = error messages not actionable enough. The telemetry grades the tool defs — def wording gets *measured*, not debated.
- **Context economics:** output-tokens trend per tool over time; pagination-depth distribution (habitual deep paging = default page_size wrong or a missing aggregate view).
- **Cost attribution:** cost/task by model from parent spans — the Phase 3 router table is a query over this, not a new system.

Dashboards answer "is it healthy"; traces answer "why was this task slow or wrong." Both are required; neither substitutes.

## Boundaries

- Never put secrets or payload *contents* in attributes — sizes and classes only (spans flow to a third party; same leak-surface rule as intent/privilege).
- Failure-taxonomy mapping: `error_type` + `data_status` count most canon classes from telemetry; **misselection is measured in Phase 2's per-question tool accuracy, not here** — different layer, stated so nobody hunts for it.

## Acceptance hook (Phase 1 gate)

The scripted 20-call session lights every attribute above in Grafana; SLI dashboard screenshot commits to the repo. Receipt, not narrative.
