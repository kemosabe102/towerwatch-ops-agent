# ADR-0006: Runbook access as a keyed section lookup, not retrieval

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door, and deliberately so** — this decision is designed to
  be *tested* rather than merely made. Phase 3 measures semantic retrieval against this
  implementation as the baseline.
- **Refs:** [`../design/06-get_runbook.md`](../design/06-get_runbook.md) (rationale and full contract), [`../specs/spec-phase3-router-and-retrieval.md`](../specs/spec-phase3-router-and-retrieval.md)

## Context and problem statement

The ops runbook holds the hard-won knowledge: known symptoms, their checks, their causes,
their procedures. The agent needs access to it during diagnosis.

"Document + LLM" reflexively suggests RAG — chunk, embed, retrieve top-k. But the actual
artifact is **one bounded document, roughly 9 KB, with ~13 symptom-indexed headings**. That
changes the calculus completely: the whole document fits comfortably in context, and the
headings already form a hand-curated index that a human wrote for exactly this
symptom-matching purpose.

Rationale is stated in [`../design/06-get_runbook.md`](../design/06-get_runbook.md); this
ADR records the decision and why the obvious alternative was rejected *for now, with a
measurement attached*.

## Decision drivers

- **The corpus is small and bounded.** ~9 KB total; a single section is a fraction of that.
- **The headings are a curated index.** A human already did the symptom→procedure mapping
  that an embedding would approximate.
- **The model is a competent matcher over ~13 enum values.** Free-text symptom → section key
  is native model work, requiring no additional layer.
- **Phase 3 needs an honest baseline.** Building RAG here first would leave the retrieval
  work with nothing to beat, and "we built retrieval" is a weaker claim than "we measured
  retrieval against the simple thing and here is the delta."

## Options considered

### Option A — keyed section lookup with a derived enum (chosen)

- **Pros:** zero infrastructure — no embeddings, no vector store, no chunking strategy, no
  refresh pipeline. Deterministic and exactly reproducible, which matters for evals.
  Returns content verbatim, so the operator gets exact commands. A miss is self-correcting
  in one turn (returns `available_sections`). Provides the measurement baseline Phase 3
  needs.
- **Cons:** does not scale past a bounded document. Cannot match on content that is not
  reflected in a heading. If the runbook grows to hundreds of sections, the enum becomes
  the def-token problem it currently solves.

### Option B — embed and retrieve top-k chunks

- **Pros:** scales to arbitrary corpora. Matches on body content, not just headings.
- **Cons:** adds an embedding pipeline, a vector store, a chunking strategy, and a refresh
  path — all to search 9 KB. Chunk boundaries can split a procedure from its preconditions,
  which is a correctness risk on operational instructions. Retrieval is non-deterministic
  in a way that complicates eval stability.
- **Why not:** rejected on cost/benefit at this corpus size, **not** on principle. Phase 3
  measures it against this baseline; if it wins, this ADR gets superseded with data behind
  the reversal.

### Option C — always return the whole document

- **Pros:** simplest possible; no enum, no miss case.
- **Cons:** spends ~9 KB of context on every call when a section is typically enough.
- **Why not:** kept as a fallback rather than the default — `full: true` exists precisely
  for this, and covers the gap when the doc grows faster than the def refreshes.

## Decision

**Option A.** `get_runbook` takes an optional `section` (enum) and an optional `full`
boolean. It returns the requested section verbatim, or the whole document when `full`.
There is no embedding, no vector store, and no semantic-matching layer — **the model is the
matcher**, selecting a section key from the enum based on the symptom described.

Content is returned verbatim and never summarized server-side: summarizing is the model's
judgment call, and an operator sometimes needs the exact command.

**This decision is explicitly a Phase 3 measurement subject.** It is not "RAG is wrong" —
it is "RAG is unjustified at 9 KB, and we are going to prove that with a number."

## Consequences

- **Positive:** no retrieval infrastructure to build, run, or keep fresh. Deterministic, so
  eval questions over the runbook are stable. Gives Phase 3 a real baseline to measure
  against — the load-the-whole-doc comparison.
- **Negative / trade-offs:** does not scale, by design. Content-level matching is
  unavailable — a symptom described in a section's body but not its heading is harder to
  find, partially mitigated by `full: true`.
- **Security consideration:** runbook content flows verbatim into model context, making this
  the repo's live tool-result injection surface. The v1 posture is a **trusted-authorship
  boundary** — the runbook is repo-controlled. A seeded-injection test targets this path;
  see [`../production-path.md`](../production-path.md) for the deferred threat model.
- **Follow-ups:** Phase 3's retrieval comparison. If semantic retrieval measurably beats
  this, supersede with the numbers attached.

## Links

- [ADR-0007](0007-derive-enums-at-server-startup.md) — how the section enum stays current.
- [ADR-0008](0008-diagnose-rca-as-a-skill-not-a-tool.md) — the same "don't build what the
  model does free" reasoning, applied to the diagnostic procedure.
