# ADR-0005: `run_speedtest` returns a server-composed before/during/after package

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door**, with a caveat: trimming the response later is
  additive-safe, but any eval question written against the `during` block would need
  rewriting.
- **Refs:** [`../design/07-run_speedtest.md`](../design/07-run_speedtest.md) (rationale and full contract), [ADR-0004](0004-budget-one-source-three-surfaces.md)

## Context and problem statement

A raw speedtest returns three numbers: down Mbps, up Mbps, bytes consumed. Those numbers
alone rarely answer the question that prompted the run. "Throughput was 12 Mbps" is not a
finding — 12 Mbps against a 200 Mbps baseline during thermal throttling on a degraded band
is a finding.

The interesting question is what the radio was doing *while* the link was saturated. That
information exists: TowerWatch's 60-second collection loop keeps running during the
speedtest, so band, carrier-aggregation state, RSRP/RSRQ/SINR, and temperature are all
being recorded across exactly that window.

Rationale is stated in [`../design/07-run_speedtest.md`](../design/07-run_speedtest.md);
this ADR records the decision and the alternative shapes weighed against it.

## Decision drivers

- **The `during` data is free.** The collection loop already captured it; composing it into
  the response costs a query, not a measurement.
- **Saturation is a diagnostic condition you cannot otherwise stage.** Radio behaviour
  under full load is exactly what a thermal or band problem reveals, and the only time it
  is observable is during a run that costs budget.
- **Round trips have a cost.** Making the agent issue a speedtest, then separately query
  the overlapping window, spends turns and invites it to query the wrong window.
- **Budget-costing calls should return maximum value per invocation** — this is the one
  tool that spends money.

## Options considered

### Option A — server composes pre / result / during / budget_after (chosen)

- **Pros:** one call returns an interpretation-ready package. The `during` window is
  computed server-side from the actual run boundaries, so it cannot be misaligned. Captures
  a condition that is expensive to reproduce. `budget_after` closes the loop for the agent's
  next decision.
- **Cons:** the largest response of any tool, and a fixed cost even when the caller wanted
  only the headline number. Couples the tool to the metrics reader as well as the speedtest
  runner.

### Option B — return the raw result; let the agent query the window itself

- **Pros:** minimal, orthogonal tools. The agent asks for exactly what it wants.
- **Cons:** requires the agent to know the precise run boundaries to align the window, and
  a slightly-wrong window silently averages in unsaturated time — a wrong answer that looks
  right. Costs at least one extra turn on the one call that spends money.
- **Why not:** the alignment failure is silent, which is the worst failure class here.

### Option C — compose pre/after, omit `during`

- **Why not:** `during` is the diagnostically valuable part. Before-and-after brackets tell
  you the link was slow; `during` tells you why.

## Decision

**Option A.** `run_speedtest` returns a server-composed package: `pre` (status snapshot
before the run), `result` (down/up Mbps, bytes, duration), `during` (concurrent radio
metrics across the run window — thermal state, band, carrier aggregation, signal),
`budget_after`, and `data_status`.

The tool is annotated **non-read-only**, so the MCP host's approval gate fires before
execution. It requires a `reason` string, logged as `triggered_by`, making every manual run
auditable.

## Consequences

- **Positive:** one budget-costing call yields a complete diagnostic picture. The `during`
  block captures radio behaviour under saturation, which is otherwise unobtainable. Window
  alignment is correct by construction.
- **Negative / trade-offs:** the biggest response payload on the surface, paid even when
  unwanted. The tool depends on both the speedtest runner and the metrics reader, so it has
  two failure modes; `data_status` must distinguish "the speedtest failed" from "the
  speedtest ran but concurrent metrics were unavailable" rather than collapsing both.
- **Observability required:** output size on the span, since this tool dominates the
  output-token distribution and would otherwise distort aggregate SLIs.

## Links

- [ADR-0004](0004-budget-one-source-three-surfaces.md) — the budget guard that decides
  whether a run happens.
- [ADR-0003](0003-cut-run-probe-from-the-tool-surface.md) — why this is the *only*
  non-read-only tool.
