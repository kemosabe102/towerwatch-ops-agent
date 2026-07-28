# Eval design — rules the golden set is built to

[`spec-phase2-eval-harness.md`](../specs/spec-phase2-eval-harness.md) is the inbound
requirement: 10 QA pairs, rubric layer, CI gate, seeded-regression showpiece. It is
frozen and not restated here. This doc carries the design rules derived *after* it —
scoring properties the spec does not specify, which the corpus must be built to satisfy.

## Why these rules live here and not in the spec

The specs are dated inbound requirements built to as a contract. Editing one to add a
later learning makes the repo's provenance claim unverifiable — a reader could no longer
tell which text was a requirement and which was backfilled. Derived decisions go in
`docs/design/` and `docs/adr/`, which already win on conflict.

## Rule 1 — "I don't know" cases require a paired positive control

The fixture contains a window where the correct answer is `insufficient_evidence`
([`10-fixture-manifest.md`](10-fixture-manifest.md), `boundary` role). That case measures
nothing on its own.

**Asserting that the right answer is "I don't know" is among the most gameable eval shapes
there is** — a model that hedges on everything scores perfectly on it. The case only
measures calibration when paired with a positive control, and **the pair is scored
together**: it passes only if the `insufficient_evidence` case is declined *and* the
control is answered. Three of the four outcomes fail — including the case worth naming
explicitly, where a model correctly declines the boundary case but also hedges the
control. Getting the hard one right does not buy the easy one.

**The rule does not amortize: every `insufficient_evidence` case needs its own control.**
One shared control across several hedge-cases reopens the loophole, because a universal
hedger then fails one pair and passes the rest by declining.

### The pair matches on request shape, not frame identity

State this explicitly, because the implementer will hit it and otherwise guess.

The `boundary` case is an `anchored_trend` request reaching past `history_available`. A
control matched on *frame identity* would be a **succeeding** `anchored_trend` request —
which requires the baseline ledger's rollup read path, deferred past Phase 2 by
[ADR-0009](../adr/0009-baseline-reference-data-beyond-retention.md) Gate 2. That control
cannot be built in Phase 2.

Matched on *request shape*, a `self_baseline` request with adequate history is a valid
control: both are "ask for a frame verdict against a reference," one should answer, one
should decline. This keeps the pair buildable in Phase 2 and the ledger deferral intact.

## Rule 2 — answer keys are committed before agent output is observed

The manifest's `expected_findings` is the answer key. Two properties:

- **Committed ahead of the first eval run, in its own commit.** After watching an agent
  answer, a curator's sense of what a window "obviously shows" drifts toward what the
  agent said — silently, and in the direction that makes results look better.
- **The harness logs the manifest commit SHA it scored against**, in the per-run metrics
  CSV the spec already requires. Git makes an edit a diff; the SHA makes a result
  traceable to the key in force when it ran. A key edited after a run becomes a version
  mismatch instead of a memory.

## Rule 3 — sparse coverage is scored as a distinct outcome

`not_collected` and `empty_window` are the load-bearing distinction in
[`00-contract-conventions.md`](00-contract-conventions.md). An eval that accepts "no
problems found" for a `not_collected` group rewards exactly the grounding failure the
envelope exists to prevent.

Cases over the fixture's `groups_absent` (see the manifest) score three-way: correct
(names the gap), wrong (reports health), or wrong (reports a problem). Only the first
passes.

## Open questions

- Whether the positive-control pair is one QA entry or two within the 10-pair budget. Two
  entries is cleaner to score; it costs a fifth of the corpus.
- Whether `reference_composition` correctness is scored at all in Phase 2, or only
  observed. It is a caveat rather than a verdict, so rubric-scored at most.
