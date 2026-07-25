# ADR-0002: Dual-mode data access via a Protocol adapter (live Grafana + committed fixture)

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** The Protocol is one interface with two
  implementations; dropping either one later is a deletion, not a redesign. Becomes
  effectively one-way once the fixture is the frozen basis of Phase 2's golden set —
  changing the data-access shape then invalidates recorded eval results.
- **Refs:** [`../design/07-run_speedtest.md`](../design/07-run_speedtest.md), [`../design/09-observability-spans.md`](../design/09-observability-spans.md), [`../specs/spec-phase2-eval-harness.md`](../specs/spec-phase2-eval-harness.md)

## Context and problem statement

The tools read TowerWatch's data from Grafana Cloud — Prometheus metrics, Loki log events,
Grafana annotations. That live source is the right thing for a demo and for real use, and
the wrong thing for tests and evals:

- **Non-deterministic.** The same eval question returns different numbers tomorrow, so a
  regression and a change in the weather look identical.
- **Time-bound.** Retention is ~2 weeks (see [ADR-0009](0009-baseline-reference-data-beyond-retention.md)),
  so any eval question pinned to a fixed window stops working once that window ages out.
- **Network- and credential-bound.** CI has neither tailnet reach nor Grafana credentials,
  and should need neither.

Phase 2's entire premise is a golden set that catches a *seeded* regression. That requires
the data underneath to be constant, or the harness measures noise.

## Decision drivers

- **Determinism is the Phase 2 gate.** Without it, "the eval caught a regression" is not a
  checkable claim.
- **CI must run offline** with no secrets and no tailnet.
- **The live path must stay real.** A fixture-only system would be a demo of a demo — the
  cross-model bench and the Inspector pass need to hit actual data.
- **TowerWatch's existing testing philosophy** already uses Protocols with hand-written
  fakes rather than mocking libraries. Continuity is worth more than novelty here.

## Options considered

### Option A — one Protocol, two implementations: `GrafanaCloudClient` and `FixtureClient` (chosen)

- **Pros:** tools are written once against an interface and never learn which mode they are
  in. Tests and evals get bit-identical inputs on every run, offline and credential-free.
  The live path stays exercised for demos and the bench. Mode is a single span attribute
  (`mode: live|fixture`), so traffic is separable in dashboards. Matches TowerWatch's
  hand-fakes convention.
- **Cons:** two implementations must be kept behaviourally aligned; a fixture that drifts
  from the live API's real shape produces evals that pass against a fiction. The fixture
  must be curated deliberately — it is a design artifact, not a dump.

### Option B — live only, with recorded HTTP cassettes for tests

- **Pros:** one implementation. Cassettes are generated rather than curated, so less
  upfront design work.
- **Cons:** cassettes couple tests to the HTTP wire format, so any client-library change
  invalidates them wholesale. They are opaque — a reader cannot tell what scenario a
  cassette encodes. Curating *which windows* the eval corpus covers becomes impossible to
  do intentionally.
- **Why not:** Phase 2's corpus needs deliberate scenario coverage (a degraded window, a
  healthy contrast, a sparse-coverage site). Cassettes make that accidental.

### Option C — fixture only, live path deferred to a later phase

- **Why not:** the Phase 1 gate includes a cross-model bench and an Inspector session
  against real data. A fixture-only Phase 1 would defer the only proof that the server
  works at all.

### Option D — a live-hitting test suite guarded by a skip marker

- **Why not:** tests that skip in CI are tests that do not run. The gate would be
  effectively unenforced while appearing green.

## Decision

**Option A.** A single data-access Protocol with two implementations. `FixtureClient`
reads a committed, curated corpus and is **authoritative for all tests and evals**;
`GrafanaCloudClient` hits live Grafana Cloud and is used for demos, the Inspector pass, and
the cross-model bench. Tools depend only on the Protocol. Every span carries
`mode: live|fixture`, and the two are never mixed in a dashboard.

`run_speedtest` is the special case: in fixture mode it returns a canned result marked
`fixture: true`, exercising the full response shape without spending bytes or needing
tailnet reach — see [`../design/07-run_speedtest.md`](../design/07-run_speedtest.md).

## Consequences

- **Positive:** evals are reproducible and CI needs no secrets. The fixture doubles as
  documentation of what the data actually looks like. Sparse coverage becomes testable
  rather than theoretical, because the fixture can deliberately include a site that lacks
  a metric group.
- **Negative / trade-offs:** the fixture can drift from live reality, and nothing detects
  that automatically — a passing eval suite is not evidence the live path works. Mitigation
  is the Phase 1 Inspector pass and the bench, both of which run live. Fixture curation is
  real design work that blocks the first implementation slice.
- **Observability required:** `mode` on every span, so a dashboard never silently blends
  fixture and live numbers.
- **Follow-ups:** fixture curation — which windows, which sites, what format — is the
  implementation-blocking input tracked separately from this ADR.

## Links

- [ADR-0001](0001-separate-repo-for-the-agent-layer.md) — why TowerWatch's data is reached
  across a repo boundary at all.
- [ADR-0009](0009-baseline-reference-data-beyond-retention.md) — the retention limit that
  makes live-backed evals untenable.
