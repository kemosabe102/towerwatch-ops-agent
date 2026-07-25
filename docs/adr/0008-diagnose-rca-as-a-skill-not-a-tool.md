# ADR-0008: Diagnosis delivered as the `diagnose-rca` skill, not a `diagnose_symptom` tool

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** The skill composes existing tools; promoting it to a
  tool later would mean moving orchestration server-side, which is additive. Nothing built
  for the skill is wasted by that move.
- **Refs:** [`../design/08-skills-interfaces.md`](../design/08-skills-interfaces.md) (full skill interface), [`../specs/spec-phase1-mcp-server.md`](../specs/spec-phase1-mcp-server.md) (candidate tool table), [ADR-0003](0003-cut-run-probe-from-the-tool-surface.md)

## Context and problem statement

The Phase 1 spec's candidate table included `diagnose_symptom` — hand the server a symptom,
get back a diagnosis. It is the headline capability: the whole system exists so someone can
ask "why is the internet bad" and get an answer.

Building it as a tool runs into the standing determinism rule: **the server interprets only
against enumerable context; the model interprets against open context.** A symptom
narrative is open context. Cross-signal attribution — deciding that degraded throughput plus
a band change plus a thermal event add up to one story — is open-context reasoning.

So a `diagnose_symptom` tool would either need an LLM inside the server (forbidden), or it
would be a fixed decision tree wearing the name "diagnose."

[`../design/08-skills-interfaces.md`](../design/08-skills-interfaces.md) states the general
placement principle — skills codify *procedures*, tools provide *capabilities*. This ADR
records why this specific capability landed on the skill side.

## Decision drivers

- **No LLM calls inside the MCP server** — a binding invariant, and diagnosis is
  irreducibly open-context work.
- **What was actually missing was procedure, not capability.** The model can already
  interpret; what it lacked was the *order* — verify the instrument before trusting the
  readings, scope before localizing, corroborate before attributing.
- **Diagnosis is gated, multi-step, and branching.** Its shape is a procedure with exit
  conditions, not a request/response.
- **"Insufficient evidence" must be a legal outcome.** A tool that returns a diagnosis is
  under pressure to always return one; a procedure can define stopping as success.

## Options considered

### Option A — a `diagnose-rca` skill composing the seven tools (chosen)

- **Pros:** keeps interpretation in the model, where the open-context reasoning belongs, and
  the server deterministic. Encodes the procedure — the six gated phases, from *verify the
  instrument* through *report* — where it is inspectable and editable without a server
  change. Per-gate attempt caps and "insufficient evidence" as a legal exit define
  done-ness. Costs zero def tokens against the 1,200-token budget.
- **Cons:** correctness depends on the model following the procedure, with no server-side
  enforcement. Skill quality is harder to unit-test than a function. Requires an MCP client
  that supports skills.

### Option B — a `diagnose_symptom` tool with an LLM inside the server

- **Pros:** one call, one answer. Works with any MCP client. Server-controlled quality.
- **Cons:** violates the no-LLM-in-the-server invariant. Puts a second model in the loop
  with its own cost, latency, and failure modes. Makes the server's output
  non-deterministic, which breaks the eval premise. Hides the reasoning the user most wants
  to see.
- **Why not:** disqualified by the invariant, and the invariant is load-bearing — it is what
  makes Phase 2's evals meaningful.

### Option C — a `diagnose_symptom` tool as a deterministic decision tree

- **Pros:** deterministic, testable, no LLM.
- **Cons:** a fixed tree cannot do cross-signal attribution over novel symptom combinations —
  exactly the case where diagnosis has value. It would encode today's known failures and be
  confidently wrong on tomorrow's.
- **Why not:** it would be a health-check tool named "diagnose," and the name would
  overpromise to the model selecting it.

## Decision

**Option A.** `diagnose_symptom` is cut from the tool surface. Diagnosis is delivered as
the **`diagnose-rca` skill** — named for the outcome, a root-cause analysis — which
composes the seven tools through a six-phase gated procedure: verify the instrument, scope,
localize, attribute, corroborate, report.

Symptom→runbook-section matching stays native model work over the derived enum
([ADR-0006](0006-runbook-keyed-lookup-not-rag.md)) — no semantic-matching layer, on the same
"don't build what the model does free" reasoning.

The division: **tools provide what the model lacks; skills codify how to proceed.** The
model was never missing the ability to interpret. It was missing the discipline to check
the instrument before trusting the reading.

## Consequences

- **Positive:** the server stays deterministic and LLM-free, keeping evals meaningful. The
  diagnostic procedure is inspectable, versionable, and editable without touching server
  code. Def-token budget goes entirely to real capabilities. The procedure's gates make
  "insufficient evidence" a legal, non-failure outcome.
- **Negative / trade-offs:** no server-side enforcement that the procedure is followed — a
  model can skip phase 0 and trust a reading from a dead collector. Phase 2's evals are the
  check, since a skipped instrument-verification shows up as a wrong answer on a
  seeded-sparse-data question. Clients without skill support get the tools but not the
  procedure.
- **Follow-ups:** if evals show the procedure being skipped systematically, the response is
  to strengthen the skill's gates — not to move interpretation server-side.

## Links

- [ADR-0003](0003-cut-run-probe-from-the-tool-surface.md) — the other cut, on capability
  rather than placement grounds.
- [ADR-0006](0006-runbook-keyed-lookup-not-rag.md) — the same reasoning applied to symptom
  matching.
