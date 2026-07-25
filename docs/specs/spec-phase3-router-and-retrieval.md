# Phase 3 spec — cost-aware router + semantic tool retrieval

Goal: two builds on top of Phases 1–2. Part A converts the rest of talk-track 16 (cost/latency engineering) to owned. Part B answers the JD's retrieval requirement in Zapier's own vocabulary — intent→action selection — and fills resume placeholder 2.

## Part A — model router (small-first, escalate on failure)

**Policy:** route every task to a small-tier model first; escalate to the large model on a failure signal (eval-check failure, malformed tool call, or explicit self-reported low confidence — implement the first two, note the third).

**Measurement (the golden set from Phase 2 is the judge):**

| Config | Success rate | Cost/task | p95 latency | Escalation rate |
|---|---|---|---|---|
| Always-large (baseline) | | | | |
| Always-small | | | | |
| Router | | | | |

**Deliverable:** the filled table + a one-paragraph verdict — where routing wins, where it costs quality, what escalation signal fired most. That paragraph is the interview answer to "how do you think about model choice balancing quality, latency, and cost."

## Part B — semantic tool retrieval (intent→action selection)

**Why this shape:** Zapier's retrieval problem is selecting the right action from 8,000+ integrations — their patents cover catalog indexing and intent-driven action mapping. Build the small version of *their* problem, not a generic doc-QA demo.

**Catalog:** the real TowerWatch tools + a **synthetic catalog of 150–250 action schemas** across familiar domains (CRM, email, calendar, chat, ticketing, storage) — generated, reviewed for plausibility, committed as JSON. Include deliberate near-duplicates (e.g., three "send message" variants) because ambiguity is the hard part.

**Retrieval pipeline:**
- Embed tool defs (name + description + param summaries); store in Chroma or sqlite-vec.
- Query = user intent phrase → top-k candidate tools.
- Compare three methods: dense-only, BM25-only, hybrid.

**Eval:** 50 intent phrasings with a labeled correct action (hand-authored; include paraphrases and trap phrasings near the duplicates). Report **precision@1 and precision@3 per method.**

**The token-economics chart (your thesis, measured):** context cost of load-all-defs vs. retrieve-then-load-top-k, plotted against selection accuracy at each k. One chart that says "here's the curve Zapier lives on" — likely the single most interview-valuable artifact in the whole build.

**Runbook side-quest (covers doc-chunking honestly, small):** chunk the TowerWatch runbook (compare 2 chunking strategies), retrieve over it for `towerwatch_get_runbook` free-text queries, report retrieval hit-rate on 15 symptom queries. This is the "indexing/chunking strategies, semantic search" JD line at honest scale — enough to discuss trade-offs from experience, no more.

## Acceptance criteria (stateless gates)

- [ ] Router table filled; all three configs run against the same golden set.
- [ ] Synthetic catalog (150+ schemas) committed with generation notes.
- [ ] Precision@1/@3 reported for all three retrieval methods on the 50-intent eval.
- [ ] Token-economics chart committed (context cost vs. accuracy vs. k).
- [ ] Runbook chunking comparison + hit-rate reported.
- [ ] README section: "what a production version needs" (pgvector, re-ranking, catalog freshness/list_changed handling — named, not built).

## Writeup

3+ surprises (hybrid-vs-dense results usually supply one; near-duplicate confusions supply another). Close with one paragraph drafted for the interview: "Here's what I learned building intent→action selection at 200-tool scale, and what I'd expect to break at 8,000."
