# Skills — interface contracts (diagnose-rca, evidence-pack)

Skills codify *procedures* (how to proceed); tools provide *capabilities* (what the model lacks). These two skills are the census questions that clustered into procedure-homes, not tool-homes. Interface level here; full skill bodies are build-time artifacts.

## Skill: `diagnose-rca`

**Renamed from `diagnose_symptom` (Anthony):** named for the outcome — what you get is a root-cause analysis, not "a diagnosis attempt." Same principle as tool naming: the name states the deliverable.

**Trigger:** a symptom is reported (by user or discovered anomaly) and the user wants cause, not just description. Serves census q1, q2, q11, q13, q14.

**Phases, each with a gate (lightweight, but defined — per Anthony's spec):**

| Phase | Work | Gate to advance |
|---|---|---|
| 0. Verify instrument | `get_monitor_status` — is the data trustworthy? | freshness OK for the sites in question, or the RCA is about the monitor (branch to runbook `silent-pi` path) |
| 1. Scope | establish when/where: window, site(s), affected layer(s) via `analyze_window` breakdown | a bounded window + at least one degraded layer identified — or exit `insufficient_evidence` |
| 2. Localize | inside walls vs ISP: gateway-layer vs wan-layer status; `compare` against healthy reference if needed | fault domain named with supporting numbers |
| 3. Attribute | within the domain, correlate signals (`query_metrics`, `query_log_events`: thermal, band/CA changes, handovers, resolver splits, event timeline) | a primary cause hypothesis with cited evidence; alternatives noted |
| 4. Corroborate | check runbook for known-issue match (`get_runbook`); optionally `run_speedtest` if a live measurement is decisive (budget-aware) | hypothesis survives or is revised against documented history |
| 5. Report | RCA: symptom → evidence → cause → confidence → recommended action (runbook section or escalation) | all claims cite tool outputs; "insufficient evidence" is a legal verdict |

**Loop-safety (Anthony's flow requirement):** max 2 attempts per gate; a gate failed twice → the skill exits with a partial RCA stating what's known, what's blocked, and the manual next step. Tool errors follow the conventions retry rules. The skill never circles back above its current phase more than once.

**Depth parameter:** novice vs expert rendering of phase 5 (same procedure, two report depths — the persona insight).

## Skill: `evidence-pack`

**Trigger:** "assemble the evidence" (census q9) — output is a *document for a third party* (ISP dispute), not an answer.

**Interface:** inputs — window, site, claim being evidenced; procedure — gather via `analyze_window` (all frames) + `query_metrics` (key series) + `query_log_events` (timeline) + `compare` (reference site/period); output — dated markdown pack: claim, methodology note (what TowerWatch is, cadence), evidence tables, timeline, honest caveats (coverage gaps). Modeled on the July 2026 standstill evidence pack.

**Gate:** every number in the pack traces to a tool call (receipts principle); no claim without a citation.

## Def-token note

Skill *descriptions* (the trigger text) follow the same economy discipline as tool defs — a skill must earn its trigger. Bodies are loaded on invocation (progressive disclosure), so body length is cheap; description length is not.
