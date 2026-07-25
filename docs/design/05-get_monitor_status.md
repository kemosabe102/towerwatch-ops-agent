# towerwatch_get_monitor_status

**Purpose:** the meta-monitoring tool — health and trustworthiness of TowerWatch *itself*, plus per-site data coverage and budget pace. Renamed from the spec's `get_probe_status` and the draft's ambiguous `get_system_status`: "monitor" says whose status this is.

**Selection sentence:** *Pick me when the question is about TowerWatch itself — is it running, is its data fresh and trustworthy, what does each site collect, how's the data budget — not about the network it watches.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `site` | enum, optional | default: all configured sites | `"home"` |

(Deliberately minimal — this is the cheap, call-it-anytime snapshot tool.)

## Response — per site

- `freshness`: age of newest sample per metric group (**the "is it lying to me" signal** — a silent Pi shows stale everything)
- `service`: running version (`build_info`), last restart, recent `collection_duration_ms` (loop health)
- `coverage`: which metric groups this site collects (**the sparse-coverage map** — feeds every other tool's `not_collected` semantics; the phone host shows its reduced set here)
- `budget`: month-to-date bytes vs 30 GB cap, current pace projection, speedtest runs today
- `data_status` per conventions

## Design notes

- Answers q8 (monitor healthy/truthful), q17 (versions/restarts), q16 (budget pace — **one source, three surfaces**: computed once in server code; surfaced here, enforced in `run_speedtest`'s guard, explained in its refusal).
- This is the diagnose skill's **step-zero tool**: verify the instrument before trusting its readings (the runbook's Silent-Pi logic, made cheap).
- Freshness thresholds (what counts as stale) are enumerable → server config, reported alongside raw ages so the model can explain.

## Errors

Grafana APIs unreachable → this tool *is* the outage detector of last resort: return what's determinable (server-side reachability result), `data_status: partial`, never pretend health.

**Def-token target: 130.**

## Open questions

- Should it include last-known chaos-harness/bench result summary? Lean no (v1) — bench is a dev artifact, not runtime state; revisit if q8 evals show a gap.
