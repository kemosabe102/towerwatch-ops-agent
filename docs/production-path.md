# Production path — personal-scale choices vs. enterprise needs

> **Status: stub, grows per phase.** This document records where a deliberate
> personal-scale choice was made, what the enterprise-scale answer would be, and what
> would trigger the change. It is not a roadmap — most of these will never be built here.

## Why this document exists

Every phase of this build makes choices sized for one person, two sites, and a hobby
budget. Those choices are correct at this scale and wrong at enterprise scale. Recording
both readings — the choice made and the choice a team would make — is the honest version
of "I know what I'm doing," and it prevents a reader from mistaking a scale-appropriate
shortcut for ignorance of the alternative.

Each entry names: **the choice here · the enterprise answer · the trigger that would force
the change.**

## Deployment and transport

- **Choice here:** stdio transport, server launched by the client. Stateless streamable
  HTTP is a Phase 1 stretch, not a gate.
- **Enterprise:** an always-on MCP gateway fronting the server — connection pooling,
  horizontal scale, health checks, versioned tool surfaces behind one endpoint.
- **Trigger:** more than one concurrent client, or any client the author doesn't control.

## Auth and multi-tenancy

- **Choice here:** none. Single user, single trust domain. Secrets live server-side and
  never enter the tool surface (*the agent holds intent; the server holds privilege*).
- **Enterprise:** per-caller identity, scoped tokens, per-tenant data isolation, audit
  trail keyed to a principal rather than to a `reason` string.
- **Trigger:** a second human, or any caller outside the tailnet.

## Retrieval and vector storage

- **Choice here:** runbook access is a keyed lookup over ~13 headings, not RAG. Phase 3
  measures semantic tool retrieval against this load-the-whole-doc baseline.
- **Enterprise:** pgvector or a managed vector store, chunking strategy, embedding
  refresh pipeline, retrieval evals as a standing CI gate.
- **Trigger:** the corpus outgrows a single bounded document, or retrieval precision
  becomes the thing being sold.

## Evaluation and drift

- **Choice here:** a committed, curated fixture is authoritative for tests and evals.
  Deterministic, offline, free.
- **Enterprise:** online sampling of real traffic, drift detection against the golden set,
  periodic re-labeling, and a process for promoting sampled cases into the corpus.
- **Trigger:** real users generating inputs the fixture never anticipated.

## Investigation triggering

- **Choice here:** investigations are human-initiated — someone asks a question.
- **Enterprise:** alert-triggered investigation, where a firing alert spawns the agent
  loop automatically and the RCA lands attached to the incident.
- **Trigger:** an on-call rotation that would rather read a draft RCA than start one.

## Baseline retention

- **Choice here:** see [`adr/0009-baseline-reference-data-beyond-retention.md`](adr/0009-baseline-reference-data-beyond-retention.md) — gated, undecided.
- **Enterprise:** a downsampled retention tier (Mimir/Thanos-style) — raw at high
  resolution for days, rollups for months, years at coarse granularity.
- **Trigger:** any question whose answer needs data older than the live retention window.

## Deferred: threat model

The design docs name a **trusted-authorship boundary** for runbook content, which flows
verbatim into model context and is therefore the repo's live tool-result injection
surface. A full threat model — injection classes, the seeded-injection test, and the
boundary's failure modes — is deferred until Phase 1 has a running server to test against.
Tracked here rather than in a stub file so the gap is visible.
