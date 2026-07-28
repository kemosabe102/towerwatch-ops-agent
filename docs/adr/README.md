# Architecture Decision Records

Each ADR captures one decision: the context, the options weighed, the choice, and its
consequences. Short, dated, numbered, append-only — superseded decisions are marked, not
deleted.

These record the decisions that produced the tool surface in [`../design/`](../design/).
Where a design doc already carries the rationale, the ADR **references it rather than
restating it** — the design docs are the contract, the ADRs are the decision history.
Duplicated rationale drifts silently.

## Index

| # | Decision | Status | Reversibility |
|---|---|---|---|
| [0001](0001-separate-repo-for-the-agent-layer.md) | Separate repo for the agent layer | Accepted (2026-07-25) | Two-way |
| [0002](0002-dual-mode-data-access-via-protocol.md) | Dual-mode data access via a Protocol adapter | Accepted (2026-07-25) | Two-way |
| [0003](0003-cut-run-probe-from-the-tool-surface.md) | `run_probe` cut from the tool surface | Accepted (2026-07-25) | Two-way |
| [0004](0004-budget-one-source-three-surfaces.md) | Budget as one computed source, three surfaces | Accepted (2026-07-25) | Two-way |
| [0005](0005-run-speedtest-server-composed-context.md) | `run_speedtest` returns server-composed before/during/after context | Accepted (2026-07-25) | Two-way |
| [0006](0006-runbook-keyed-lookup-not-rag.md) | Runbook access as keyed lookup, not RAG | Accepted (2026-07-25) | Two-way |
| [0007](0007-derive-enums-at-server-startup.md) | Enums derived from their sources at server startup | Accepted (2026-07-25) | Two-way |
| [0008](0008-diagnose-rca-as-a-skill-not-a-tool.md) | Diagnosis as a skill, not a tool | Accepted (2026-07-25) | Two-way |
| [0009](0009-baseline-reference-data-beyond-retention.md) | Baseline reference data beyond the retention window | **Proposed · 1 gate open** | Two-way |

## Conventions

Written to the author's ADR conventions: `NNNN-short-title.md`, zero-padded, sequential.
Settled decisions use the standard shape; decisions blocked on unanswered questions use
the **gated** shape, where each gate carries a decision rule ("if the answer is X, the
outcome is Y").

**Title rule:** a title states only what no open gate can revoke. ADRs 0001–0008 are
settled, so they name their mechanism. [0009](0009-baseline-reference-data-beyond-retention.md)
has a gate that can route to do-nothing, so its title names the topic only — it retitles
when the gate closes.

## Status legend

- **Proposed** — context captured, decision not yet made. A gated ADR adds its open-gate
  count.
- **Accepted** — decided and in effect.
- **Superseded by ADR-NNNN** — replaced by a later ADR.
- **Deprecated** — no longer relevant, not replaced.

A gated ADR resolves to **Accepted on either branch** — a failed gate accepts the
do-nothing option; it does not kill the doc.
