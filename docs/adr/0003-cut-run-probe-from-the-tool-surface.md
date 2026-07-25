# ADR-0003: `run_probe` cut — the 60-second collection loop is the probe

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** Adding a tool later is additive and costs nothing
  already built. The cost of being wrong is a deferred capability, not rework.
- **Refs:** [`../specs/spec-phase1-mcp-server.md`](../specs/spec-phase1-mcp-server.md) (candidate tool table), [`../design/00-contract-conventions.md`](../design/00-contract-conventions.md), [ADR-0005](0005-run-speedtest-server-composed-context.md)

## Context and problem statement

The Phase 1 spec's candidate tool table included `run_probe` — an on-demand trigger to
execute a network probe (ping, DNS lookup, TCP connect) right now and return the result.
It is the obvious tool to want: the agent is diagnosing a network, so let it poke the
network.

TowerWatch already runs a **60-second collection loop** that probes continuously and
persists the results. So the question is not "should the system probe" — it already
does — but "does the agent need to trigger an *additional* probe out of band."

## Decision drivers

- **This is an analytical system, not a control system.** Every census question it was
  designed against asks *what happened* or *what is happening*, not *make something
  happen*.
- **Freshness is already ≤60 seconds.** An on-demand probe's marginal value is bounded by
  that gap — it can only tell you about the last minute.
- **Every tool costs def tokens** against a hard 1,200-token budget, and costs selection
  clarity: a seventh near-neighbour makes the model's choice harder for all the others.
- **Write-capable tools carry a different risk class.** `run_probe` executes something on a
  remote host; read tools cannot.

## Options considered

### Option A — cut it; rely on the 60-second loop (chosen)

- **Pros:** removes a tool whose value ceiling is one minute of freshness. Keeps the
  surface read-only except for the one tool that genuinely must not be
  ([`run_speedtest`](../design/07-run_speedtest.md)). Frees def-token budget for the
  interpretive tools that carry more weight. Sharpens the surface: every remaining tool
  answers "what does the data say," and exactly one performs an action.
- **Cons:** a genuinely live check — "is it broken *right now*, this second" — has no
  tool. During an active incident the agent waits up to 60 seconds for the loop rather
  than forcing an immediate answer.

### Option B — keep `run_probe` as a general on-demand prober

- **Pros:** sub-minute answers during active incidents. Can probe targets the loop does not
  cover.
- **Cons:** duplicates the collection loop's job with a second, agent-triggered path that
  could disagree with it. Requires remote execution on the Pis, so it inherits the tailnet
  and SSH-identity requirements that otherwise only `run_speedtest` carries. Needs its own
  rate guard to prevent an agent loop from hammering a target.
- **Why not:** it buys ≤60 seconds of latency at the cost of a second execution path, a
  second guard, and a muddier tool surface. The trade is not close.

### Option C — keep it, but scoped to targets the loop does not cover

- **Why not:** the coverage gap is hypothetical. If a target matters enough to probe
  on demand, it belongs in the collection loop's config — that is a TowerWatch change, not
  an agent tool.

## Decision

**Option A.** `run_probe` is cut from the tool surface. Live network state is read through
[`query_metrics`](../design/01-query_metrics.md) and
[`analyze_window`](../design/02-analyze_window.md) over data no more than 60 seconds old.
`run_speedtest` remains the sole non-read-only tool, because a throughput measurement is
genuinely unavailable any other way and is not on a 60-second loop.

The distinction that decides it: **`run_speedtest` measures something the loop does not
continuously collect; `run_probe` would re-measure something it already does.**

## Consequences

- **Positive:** six of seven tools are `readOnly`, so exactly one host approval gate exists
  and it is meaningful. Def-token budget goes to the interpretive tools. Selection stays
  clean — no "should I query or probe?" ambiguity for the model.
- **Negative / trade-offs:** worst-case 60-second staleness during an active incident, with
  no way to force fresher data. If a real diagnosis is ever blocked by that wait, this ADR
  should be revisited — the reversal is cheap.
- **Follow-ups:** if Phase 2 evals show questions failing specifically because of the
  freshness gap, that is the evidence to reopen this. Absent that evidence, the cut stands.

## Links

- [ADR-0005](0005-run-speedtest-server-composed-context.md) — why the one remaining action
  tool earns its place.
- [ADR-0008](0008-diagnose-rca-as-a-skill-not-a-tool.md) — the other surface cut, on
  different grounds (procedure, not capability).
