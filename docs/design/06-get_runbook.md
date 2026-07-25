# towerwatch_get_runbook

**Purpose:** keyed access to the ops runbook — the documented, hard-won knowledge of known symptoms and their procedures. Deliberately *not* retrieval: one bounded, symptom-indexed document (decision #6; Phase 3 measures RAG against this baseline).

**Selection sentence:** *Pick me when you want what we've already documented about a known symptom — the checks, causes, and procedures from past incidents. For live data, use the query/analyze tools.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `section` | enum, optional | **derived from the runbook's headings at server startup** (living document — the doc is the single source of truth; the def cannot drift stale) | `"silent-pi"` |
| `full` | bool | default `false`; `true` returns the whole document (it fits — ~9 KB) | — |

## Response

Requested section's content (markdown, verbatim), or whole doc when `full`. On a `section` miss: `available_sections` list + suggestion to retry with a valid key or `full: true` — the miss is self-correcting in one turn.

## Design notes

- **The model is the matcher.** Free-text symptom → section key is native model work over ~13 enum values; no semantic-matching layer (decision #8 rationale — don't build what the model makes free).
- The living-document concern is handled structurally: new runbook sections appear in the enum at next server start, and `full: true` covers the gap between doc growth and def refresh.
- **Injection note (canon class #5, B-17 thread):** runbook content flows verbatim into model context — this is the repo's live tool-result injection vector. v1 posture: the runbook is repo-controlled (trusted-authorship boundary); the threat-model doc states this assumption explicitly, and the planned seeded-injection test targets exactly this path.
- Content returned verbatim, never summarized server-side — summarizing is the model's judgment call, and the operator sometimes needs exact commands.

## Errors

Unknown section → `available_sections` + `retryable: true` (the actionable-miss contract). Runbook file missing/unparseable → non-retryable, names the repo path to fix.

**Def-token target: 120** (smallest def — enum carries most of the information).

## Open questions

- Whether `available_sections` should also appear proactively in `get_monitor_status` or stay error-only. Lean error-only (def-token economy); revisit if evals show section-guess misses are common.
