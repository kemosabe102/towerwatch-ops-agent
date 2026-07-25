# ADR-0007: Schema enums derived from their sources at server startup

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door.** Freezing a derived enum into a literal later is
  trivial. The reverse — discovering hardcoded values have drifted — is the expensive
  direction, which is why derivation is the default.
- **Refs:** [`../design/06-get_runbook.md`](../design/06-get_runbook.md) (rationale), [`../design/00-contract-conventions.md`](../design/00-contract-conventions.md), [`../design/04-query_log_events.md`](../design/04-query_log_events.md)

## Context and problem statement

Three tool parameters are enums whose valid values are defined somewhere else in the system:

- `get_runbook`'s **`section`** — defined by the runbook's headings.
- **`site`** — defined by the configured sites (currently `standstill`, `home`).
- `query_log_events`'s **`event_types`** — defined by the known event vocabulary.

Each has a source of truth that is not the tool definition. Writing the values into the
schema as literals creates two copies of one list, and the copies diverge the moment
someone edits the source — a new runbook section, a third site, a new event type.

Divergence here is **silent and asymmetric**: the tool keeps advertising the stale list, so
the model never asks for the new section and never learns it exists. Nothing errors. The
capability is simply invisible.

Rationale is stated in [`../design/06-get_runbook.md`](../design/06-get_runbook.md) for the
runbook case; this ADR generalizes it to the pattern and records the alternatives.

## Decision drivers

- **The failure mode of the hardcoded version is silence,** not a crash. That is the worst
  class — nothing surfaces the problem.
- **A tool definition is a prompt.** A stale enum does not just lose a capability; it
  actively misinforms the model about what exists.
- **The runbook is a living document.** It grows exactly when incidents teach something new
   — which is precisely when the agent most needs the new section.
- **Structural verification beats review effort.** Deriving the list from its defining
  source makes drift impossible rather than merely detectable.

## Options considered

### Option A — derive at server startup from the source (chosen)

- **Pros:** the definition cannot drift stale; the source of truth stays singular. New
  runbook sections, sites, or event types appear automatically on next server start.
  Requires no discipline from a future maintainer. Matches the "make wrong output fail
  loudly rather than relying on a reader noticing" principle.
- **Cons:** the enum is not visible by reading the source code alone, so a reader must know
  where it comes from. A malformed source (unparseable runbook, bad config) becomes a
  startup failure. Values can change between server restarts within one session.

### Option B — hardcode the values in the Pydantic schema

- **Pros:** explicit and greppable; the schema is self-documenting; no startup parsing.
- **Cons:** two copies of one list, guaranteed to diverge, failing silently when they do.
  Every runbook edit becomes a code change nobody will remember to make.
- **Why not:** the silent-drift failure mode is disqualifying for a system whose entire
  premise is that absence must never be mistaken for evidence.

### Option C — derive at build time, commit the generated enum

- **Pros:** visible in source; no startup cost; drift caught by a diff in review.
- **Cons:** needs a codegen step and a CI check that the committed output matches the
  source, or it silently rots exactly like Option B.
- **Why not:** more machinery than parsing headings at startup, for a system where the
  runbook lives in a sibling repo and would not trigger this repo's build anyway.

## Decision

**Option A.** The `section`, `site`, and `event_types` enums are **derived at server
startup** from their defining sources — the runbook's headings, the configured sites, and
the known event vocabulary respectively. No enum values are hardcoded in tool schemas.

Two structural safeguards handle the residual gap:

- `get_runbook` accepts `full: true`, covering the window between the document growing and
  a server restart picking it up.
- An unknown enum value returns the **valid values plus `retryable: true`**, so a miss is
  self-correcting in one turn rather than a dead end.

## Consequences

- **Positive:** tool definitions cannot advertise a stale vocabulary. The runbook, site
  config, and event vocabulary each stay singular sources of truth. Adding a runbook
  section requires no code change at all.
- **Negative / trade-offs:** enum values are not discoverable by reading the schema alone.
  A malformed source fails at startup — loud, and preferable to a silently wrong enum, but
  it does mean the server will not boot on a broken runbook. Long-running sessions can hold
  a stale enum until restart.
- **Observability required:** the derived enum sizes should be logged at startup, so "the
  runbook parse silently found zero sections" is visible rather than presenting as an empty
  dropdown.

## Links

- [ADR-0006](0006-runbook-keyed-lookup-not-rag.md) — the lookup design this enum serves.
- [`../design/00-contract-conventions.md`](../design/00-contract-conventions.md) — the
  derive-don't-hardcode rule as a standing convention.
