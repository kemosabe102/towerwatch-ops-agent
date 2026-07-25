# towerwatch_compare

**Purpose:** deterministic comparison across one dimension — two time periods, or two hosts — with aligned windows, computed deltas, and honest intersection semantics. Exists because diff arithmetic belongs in code, not in a model reading two prose summaries.

**Selection sentence:** *Pick me when the question is inherently relational — is A worse than B — across time or across hosts. For a single window's health, use `analyze_window`.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `dimension` | enum | `time_periods` \| `hosts` | `"hosts"` |
| `a`, `b` | object | each: `{site, start, end}`; for `time_periods`, same site both sides; for `hosts`, windows should overlap (warned if not) | `{"site":"home", ...}` |
| `metric_groups` | list[enum], optional | default: all groups present on **both** sides | `["latency","throughput"]` |

## Response

- Per-metric **distribution block**, both sides: `{sample_count, mean, p50, p95, p99, max, min, stddev}` — with delta and delta-% on each statistic, computed over the **comparable intersection** only. Mean-only comparison is malpractice on network data: the outliers *are* the story (a link with identical means and a 4× p99 is the degraded one), and tail-vs-median divergence is itself diagnostic (bufferbloat, bursts).
- `not_comparable`: named list of metrics/groups present on one side only, with which side lacks them (the phone-vs-Pi case: phone lacks signal/hardware groups — say so, never silently narrow).
- `alignment_notes`: window durations, sample counts per side (asymmetric density flagged — a 2-sample side vs a 2,000-sample side is not a fair mean).
- `data_status`, `coverage_notes` per conventions.

## Design notes

- **Cross-host is the census-driven addition** (q3: phone vs site — the July evidence-pack question). The spec's `compare_periods` becomes one dimension of a general comparator.
- **Standing hypothesis (Phase 2 falsifies):** the `time_periods` dimension may be redundant with two `analyze_window` calls + model diffing. Keep it if evals show models fumble the two-call composition or the arithmetic; cut the dimension if they don't. Either outcome is a documented decision with data behind it.
- No judgment in the response — deltas, not verdicts. "Is this delta *bad*" is `analyze_window`'s frames or the model's reasoning.

## Errors

Non-overlapping windows on `hosts` dimension → warn, proceed, flag in `alignment_notes`. Zero comparable metrics → actionable error naming each side's available groups, `retryable: true` with narrowed request.

**Def-token target: 180.**

## Quality bar and deferred depth

`compare`, `analyze_window`, and `query_metrics` are the core three — the distribution block above is v1's quality floor, not its ceiling. Deferred comparison dimensions, named so deferral is a decision: time-of-day profile comparison (diurnal patterns), event-frequency comparison (outage/restart counts per side), distribution-shape tests (beyond point statistics). Each waits for a census question or eval failure that demands it — YAGNI until pulled.

## Open questions

- Should `hosts` accept >2 sites (n-way)? Census says no (all comparative questions are pairwise) — YAGNI until a question demands it.
