# ADR-0004: Data budget computed once in server code, exposed through three surfaces

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** Moving the computation later is an internal
  refactor behind unchanged tool contracts.
- **Refs:** [`../design/05-get_monitor_status.md`](../design/05-get_monitor_status.md) (rationale), [`../design/07-run_speedtest.md`](../design/07-run_speedtest.md) (guard + refusal)

## Context and problem statement

The connection has a **30 GB/month cap**, and `run_speedtest` consumes real bytes per run.
Three different things need to know the budget state: the agent deciding whether to
suggest a speedtest, the server deciding whether to permit one, and the refusal message
explaining why one was denied.

Three consumers of one number is where drift starts. If each computes its own, they
disagree — and the disagreement surfaces as a tool that refuses while the status tool
reports headroom.

Rationale for the chosen shape is stated in
[`../design/05-get_monitor_status.md`](../design/05-get_monitor_status.md); this ADR records
the decision, what was weighed against it, and why the enforcement point is where it is.

## Decision drivers

- **Money is real.** Exceeding the cap has a cost that no amount of model discipline can
  refund.
- **Three surfaces must never disagree**, because a contradiction between them is worse
  than either answer alone — it teaches the model the tools are unreliable.
- **Guidance is not enforcement.** A budget rule stated in a prompt is advisory; the
  Phase 3 router will send smaller models here, and the guard has to hold for all of them.

## Options considered

### Option A — computed once server-side, surfaced in three places (chosen)

- **Pros:** one code path, so the three surfaces cannot contradict each other. Enforcement
  sits server-side where it is not model-relative. The refusal can quote the same numbers
  the status tool reports, so the agent's next move is obvious.
- **Cons:** couples three tool responses to one internal component; a bug in it is visible
  in three places at once (which is also arguably a feature — it fails loudly).

### Option B — the agent tracks spend across the conversation and self-limits

- **Pros:** no server-side state at all.
- **Cons:** relies on model discipline for a spending limit. Fails on a fresh session, on
  context truncation, or on any model that reasons less carefully. Cannot see spend from
  other sessions or from TowerWatch's own scheduled runs.
- **Why not:** *never rely on model discipline for money* — the conventions doc's rule, and
  the decider here.

### Option C — each tool computes budget independently when it needs it

- **Why not:** three implementations of one arithmetic rule, guaranteed to drift. This is
  the failure mode the decision exists to prevent.

### Option D — enforce only in `run_speedtest`, expose nowhere

- **Why not:** the guard would work, but the agent gets no pacing signal and would keep
  proposing runs it cannot make. A refusal the caller could have predicted is a wasted turn.

## Decision

**Option A.** Budget state — month-to-date bytes against the 30 GB cap, pace, and runs
today — is computed **once in server code** and exposed through exactly three surfaces:

1. **Pace**, reported by [`get_monitor_status`](../design/05-get_monitor_status.md) — the
   agent's read on available headroom.
2. **The guard** inside [`run_speedtest`](../design/07-run_speedtest.md) — hard, server-side
   enforcement that refuses when a run would threaten the cap.
3. **The refusal message** — actionable, naming current usage, the cap, the reset date, and
   the alternative (recent scheduled results via `query_metrics`).

`run_speedtest` also returns `budget_after`, closing the loop so the agent's next decision
uses post-run numbers.

## Consequences

- **Positive:** the three surfaces are consistent by construction. Overspend is prevented
  by code, not by prompt wording. Refusals teach the agent what to do next instead of
  dead-ending.
- **Negative / trade-offs:** the budget component becomes load-bearing for three tools, so
  it needs its own tests. Byte-cost estimation per speedtest is approximate, so the guard
  must be conservative — it will occasionally refuse a run that would have fit.
- **Observability required:** budget state at refusal time should be visible in the span,
  so a "why did it refuse" question is answerable from traces.

## Links

- [ADR-0005](0005-run-speedtest-server-composed-context.md) — the tool the guard protects.
- [`../design/00-contract-conventions.md`](../design/00-contract-conventions.md) — the
  loop-safety rule this instantiates: hard limits live server-side, where cost is real.
