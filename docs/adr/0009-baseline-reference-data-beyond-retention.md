# Baseline reference data beyond the retention window

- **Status:** Proposed · 2 gates open — review requested
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** A ledger is additive — an append-only side store that
  no tool contract depends on until a frame consumes it. Deleting it later loses history,
  not correctness.
- **Refs:** [`../design/02-analyze_window.md`](../design/02-analyze_window.md) (retention constraint, frame table), [ADR-0002](0002-dual-mode-data-access-via-protocol.md)

## Executive summary

We recommend persisting **daily per-metric rollup aggregates to a small local store** — a
baseline ledger — so `analyze_window`'s `anchored_trend` frame can see past the ~2-week
live retention window, **conditional on two gates**: whether slow-drift detection is
actually required (Gate 1) and whether the ledger must exist before Phase 2 freezes its
golden set (Gate 2). If Gate 1 shows a ~13-day `self_baseline` answers the real questions,
the correct outcome is do-nothing at zero cost, and `anchored_trend` ships reporting
`insufficient_evidence` honestly. If drift detection is required, the ledger is roughly a
day of work and no new infrastructure.

## Gates

### Gate 1 — Is slow-drift detection required? (decides build vs. do-nothing)

**Question:** Does any question this system must answer require comparing a window against
a reference period older than ~13 days?
**Decision rule:** If every real question is answerable within retention, adopt the
do-nothing branch — ship `anchored_trend` returning `insufficient_evidence` beyond
`history_available` — and close this ADR. If months-scale comparison is genuinely needed,
proceed to build the ledger.
**Status:** Open. Needs the census questions reviewed specifically for time horizon, and a
judgment on whether "is it slowly getting worse?" is a question worth answering here.

### Gate 2 — Must the ledger predate Phase 2's golden set?

**Question:** Will Phase 2's eval corpus contain questions whose answers depend on
pre-retention reference data? (Fixture mechanics: see Context.)
**Decision rule:** If the golden set pins all its windows inside retention and the fixture
supplies its own baselines, the ledger can be deferred past Phase 2 as a live-mode-only
enhancement. If any eval question needs a real long-horizon baseline, the ledger must land
before the corpus is frozen.
**Status:** Open. Blocked on fixture curation, which decides what the eval corpus can ask.

## Context

The environment retains **~2 weeks** of queryable data — a binding constraint recorded in
[`../design/02-analyze_window.md`](../design/02-analyze_window.md) and dated 2026-07-24.
Two consequences were designed in rather than discovered:

- `self_baseline` uses a trailing window of ≤ ~13 days, which fits comfortably.
- `anchored_trend` — the frame that catches slow creep, the 1%-per-week failure — **cannot
  see past retention from live queries**. Months-scale drift is undetectable without
  persisted history.

Every frame response already reports `history_available` honestly, and a request exceeding
it returns `insufficient_evidence` for that frame rather than a silently-shortened answer.
So the do-nothing branch is already implemented and already correct — it simply cannot
answer a class of question.

### Load-bearing mechanic — the fixture is not affected by retention

Tests and evals run against a committed fixture
([ADR-0002](0002-dual-mode-data-access-via-protocol.md)), not live queries. A fixture can
contain whatever history its curator puts in it, including synthetic long-horizon
baselines. This is why Gate 2 is a separate question from Gate 1: the ledger could be
unnecessary for evals while still being necessary for live use.

## Options

### Option A — baseline ledger: daily rollups to a local store (recommended)

**Why here:** it is the smallest thing that survives retention — a downsampled retention
tier at hobby scale, which is the same shape real deployments reach for.

- Daily per-metric aggregates (count, mean, p50, p95, p99, max), appended on a schedule to
  JSON or SQLite.
- Storage is trivial — one row per metric per day.
- **[TO VALIDATE]** Whether TowerWatch or the MCP server owns the rollup job. The server
  owning it keeps this repo self-contained; TowerWatch owning it puts the job next to the
  data. Leaning server-side, per [ADR-0001](0001-separate-repo-for-the-agent-layer.md)'s
  one-way dependency rule.

### Option B — extend Grafana Cloud retention (runner-up)

Viable and nearly zero-effort. **Rejected on cost and ceiling:** it is a recurring bill for
a hobby project, and paid retention still has a horizon — it defers the problem rather than
solving it. **Conditional re-rank:** if the plan's retention were already sufficient at no
extra cost, this dominates Option A outright.

### Rejected outright

| Option | Why rejected |
|---|---|
| Full raw-metric archival | Storage grows without bound to answer questions that only need aggregates. |
| Recompute baselines on demand from live data | Impossible by definition — the data is gone past retention. |
| Hardcode static threshold tables as the only reference | Already covered by the `type_profile` frame; answers "bad for cable," not "worse than it was." |

## Decision

**Gate first.** If Gate 1 shows every real question is answerable within ~13 days, adopt the
do-nothing branch: `anchored_trend` ships as specified, reporting `insufficient_evidence`
beyond `history_available`, and this ADR closes as Accepted on that branch. If drift
detection is required, build Option A — with the frame API designed to consume the ledger
from the start, so the ledger becomes a data-availability change rather than a contract
change. Gate 2 decides only its *timing* relative to Phase 2, not whether it is built.

## Consequences

- **Positive:** `anchored_trend` becomes genuinely useful rather than structurally
  limited. The rollup store is small, local, and needs no new infrastructure. Designing the
  frame API to consume it now keeps the later build additive.
- **Negative:** a second data path with its own correctness question — a rollup job that
  silently stops leaves a gap that looks exactly like a quiet period. Rollups are lossy by
  construction, so any question needing raw resolution past retention stays unanswerable.
- **Observability required:** ledger write freshness must be visible in
  `get_monitor_status` alongside collection freshness. A stalled rollup job is otherwise
  indistinguishable from a working one until a frame silently loses history.

## Validation plan

1. Answer Gate 1.
2. Answer Gate 2.
3. Baseline window length within retention — pick the trailing-window figure for
   `self_baseline` and record it as config.
4. Anchor period selection, once the ledger exists — which fixed period is the reference.
5. Rollup job ownership — server-side vs. TowerWatch-side, per the open validation above.

## Follow-up work (not scoped here)

- Fixture curation decides what the eval corpus can ask, and therefore answers Gate 2.
  Tracked as the implementation-blocking design input before the first code slice.
- Enterprise-scale comparison (Mimir/Thanos-style downsampled tiers) is recorded in
  [`../production-path.md`](../production-path.md).

## Evidence

- **E1** — retention constraint, ~2 weeks queryable: recorded and dated 2026-07-24 in
  [`../design/02-analyze_window.md`](../design/02-analyze_window.md), "Retention constraint
  (binding)".
- **E2** — frame table (`self_baseline` / `type_profile` / `anchored_trend`), each frame's
  catch and blind spot: same document, "Reference frames" section.
- **E3** — fixture authority for tests and evals:
  [ADR-0002](0002-dual-mode-data-access-via-protocol.md).
