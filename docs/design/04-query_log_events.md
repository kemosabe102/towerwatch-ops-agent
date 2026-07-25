# towerwatch_query_log_events

**Purpose:** access to the event record — structured Loki log events and Grafana outage annotations — the "what happened" complement to the "how were the numbers" tools. Name is source-explicit by design (logs, not metrics).

**Selection sentence:** *Pick me when you need discrete events — outages, restarts, push failures, speedtest completions, chaos events — rather than continuous measurements.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `site` | enum | required | `"standstill"` |
| `start`, `end` | ISO-8601 | required | — |
| `event_types` | list[enum], optional | enum derived from the known event vocabulary (metrics-inventory §10: `connection_down`, `service_restarted`, `metrics_push_failed`, …); default all | `["connection_down"]` |
| `include_annotations` | bool | default `true` — Grafana outage annotations interleaved, marked by origin | — |
| `page_size`, `page_token` | — | per conventions | — |

## Response

Chronological event list (`timestamp`, `event`, `origin: loki|annotation`, structured fields), `data_status`, `truncated`/`next_page_token`.

## Design notes

- **Generalizes the spec's `list_chaos_events`:** chaos events are one `event_types` filter, not a tool. One def serves q4 (what happened in this window), q8 (monitor lifecycle events), q13 (annotation investigation).
- `empty_window` here is *meaningful evidence* (no outage events ≈ no detected outages) — but only when `data_status` distinguishes it from `not_collected` and from the known gap that failed Loki pushes are currently swallowed silently (runbook §Loki push failing). That known gap gets one honest clause in the def or response notes: absence of events during a push-failure period is not evidence.
- Event vocabulary is derived from config at startup (same derive-don't-hardcode rule).

## Errors

Unknown event type → actionable (valid vocabulary), `retryable: true`. Annotation API unreachable but Loki fine → `partial`, annotations flagged missing, not a hard error.

**Def-token target: 150.**

## Open questions

- Should annotation *writes* (e.g., the agent marking an investigated window) ever exist? Out of scope v1 — read-only surface; noted for production-path.
