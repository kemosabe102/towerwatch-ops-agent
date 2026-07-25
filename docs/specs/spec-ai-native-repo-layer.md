# Spec — AI-native repo layer (the onboarding showcase)

Goal: make the TowerWatch Ops Agent repo itself a demonstration artifact — a repo where a fresh AI session becomes productive immediately, where the golden paths are codified as skills, and where agent work passes through the same gates as human work. This layer is what proves "I know what I'm doing" beyond the features; it is the JD's "codify practical agent patterns" and "share your workflows" rendered as a working repo.

**Interface note:** the exact agent/sub-agent design is being developed in a separate session. This spec defines *what must exist in this repo and what it must demonstrate* — the contract that design plugs into — not the internals of the agents themselves.

## What gets shown off, and what each element proves

| Showcase element | What it proves in an interview |
|---|---|
| Root `CLAUDE.md` + progressive-disclosure doc tree | Context-economics judgment: the same token discipline applied to tool defs (Phase 1) applied to repo knowledge |
| In-repo skills (golden paths as code) | "Codify practical agent patterns" — JD language, as artifacts |
| ADRs written to your published rubric | The S3 golden-guidelines story, public and inspectable |
| Primary agent + scoped sub-agent + reviewer pass | Governance from your principles framework — including the fresh-eyes reviewer as *a single check, not triangulation* (your own spec's distinction) |
| Evals gating agent-authored changes | Stateless gates: agents that modify tools are caught by the repo's own eval harness in CI |
| **Measured onboarding (the crown jewel)** | AI-friendliness as a metric, not a vibe — almost nobody can claim this |
| Tool-def token report (`def_tokens.md`) | Token economics, quantified |

## Required artifacts

### 1. Agent-facing documentation architecture
- **Root `CLAUDE.md`, ≤ ~150 lines:** project mental model (3 sentences), architecture pointer, commands, conventions, gotchas, and links to deeper docs. Written for agents: terse, imperative, example-bearing. Hard rule mirrored from Phase 1: the root file has a token budget — measure it, state it in the file's header.
- **Progressive disclosure:** deep context lives in `docs/` (architecture + data-flow diagram, eval philosophy, testing strategy), loaded on demand — never front-loaded. The doc tree's design rationale gets one paragraph in the README: this *is* the tool-def token lesson applied to knowledge.
- **ADRs (`docs/adr/`):** every decision the build plan records (language choice, transport, vector store, router policy) becomes an ADR written to your published ADR guidelines — the rubric file committed alongside, so readers see the standard *and* the outputs it produced.

### 2. In-repo skills — golden paths as code
Minimum set (add only what the build actually uses):
- **`add-tool`** — scaffolds a new MCP tool: Pydantic schema with examples, OTel span wiring, def-token check, eval-stub reminder. The golden path for the most common change.
- **`run-evals`** — runs the Phase 2 harness locally with a readable report.
- **`write-adr`** — generates an ADR draft against your rubric and self-scores it.
- **`bench`** — runs the cross-model bench and updates `bench.md`.

Each skill's description follows the same discipline as tool defs: it must earn its trigger. A skill nobody (human or agent) invokes is scope creep — delete it.

### 3. Agent architecture hooks (contract for the other session's design)
- A **primary agent** entry point documented in `CLAUDE.md` (how a session starts, what it loads first).
- A **worker sub-agent** scoped to in-repo changes, inheriting repo conventions.
- A **reviewer pass** — one fresh-eyes check on agent-authored diffs before human review. Per your framework: it is a single check, never credited as triangulation.
- All three documented at interface level here; internals arrive from the other session's design.

### 4. Verification structure agents can use
- `make verify` (or task-runner equivalent): lint, type-check, unit tests, def-token check, eval smoke — one command an agent can run and quote as a receipt.
- CI identical to local `verify` — stateless gates, same checks regardless of author.
- PR template asks for receipts: "paste the verify output."

### 5. The onboarding eval (the measurable claim)
A scripted golden onboarding task, run against a **fresh AI session with zero conversation history**:

> Standard prompt: "You've just been added to this repo. Add a `towerwatch_get_uptime` tool end-to-end: schema, implementation, span, def-token check, eval stub. Use the repo's skills."

**Measure:** turns to completion · wall time · human interventions needed · gates passed on first try. Run it at least twice (after Phase 1 and after Phase 2), record both runs in `docs/onboarding-eval.md`, and put the headline number in the README ("a fresh agent session ships a conforming tool in N turns"). If the number is embarrassing on run one, that's the story — what you changed between runs is the interview answer about making repos agent-legible.

## Build sequencing — anti-scope-creep rules

This layer is **incremental alongside the phases, never a blocking fourth phase:**
- Day one of Phase 1: root `CLAUDE.md` + first ADRs (they're nearly free while decisions are fresh).
- Skills: created the first time their golden path is walked manually, not before.
- Onboarding eval: first run after Phase 1 completes; second after Phase 2.
- Total incremental budget: **2–4 days across the three weeks.** If it's consuming more, cut skills, not phases — Phase 1 still gates submission and nothing here changes that.

## Acceptance criteria (stateless gates)

- [ ] Root `CLAUDE.md` ≤ budget, token count stated in header.
- [ ] ≥ 4 ADRs to the rubric, rubric committed.
- [ ] ≥ 3 skills present, each invoked at least once during the real build (receipt: reference in a PR).
- [ ] `make verify` green locally and in CI; PR template requests receipts.
- [ ] Onboarding eval run twice, both recorded, headline number in README.
- [ ] Interface doc for primary/sub-agent/reviewer present (internals may say "designed in companion project").

## Interview framing (one paragraph, drafted for reuse)

"The repo is the enablement artifact. Anyone — human or agent — gets the same golden paths: skills for the common changes, ADRs so decisions don't get relitigated, one verify command, and evals that gate every change regardless of who authored it. And I measure the claim: a fresh agent session ships a conforming tool in N turns. That's what I mean by making a team AI-ready — codified paths, stateless gates, and an onboarding number you can watch improve."
