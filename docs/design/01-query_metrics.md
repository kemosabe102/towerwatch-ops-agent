# towerwatch_query_metrics

**Purpose:** raw, paginated time-series access — the exploratory substrate. Returns numbers for the model to reason over; performs no interpretation.

**Selection sentence:** *Pick me when you need the actual data points — specific values, series, timestamps — and you'll do your own reasoning. If you want a judgment about a window, use `analyze_window` instead.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `site` | enum (startup-derived) | required | `"standstill"` |
| `metric_group` | enum | required — `latency` \| `throughput` \| `dns` \| `tcp` \| `gateway` \| `speedtest` \| `bufferbloat` \| `signal` \| `cell_identity` \| `hardware` \| `meta` | `"latency"` |
| `metrics` | list[str], optional | narrows within the group; invalid names error with the group's valid list | `["rtt_avg_google"]` |
| `start`, `end` | ISO-8601 | required; max range enforced (e.g. 31 d) to bound payloads | `"2026-07-20T00:00:00-07:00"` |
| `step` | str, optional | downsample resolution (`"5m"`, `"1h"`); default auto by range | `"15m"` |
| `page_size`, `page_token` | int / str | pagination per conventions | — |

## Response

Series (metric → [timestamp, value] pairs, downsampled per `step`), `data_status`, `coverage_notes`, `truncated`, `next_page_token`.

## Design notes

- **Metric-group enum is the vocabulary surface.** 74 metric names never appear in the def — groups map to the inventory's sections; full names are discoverable via results and error messages (progressive disclosure inside a schema).
- Auto-downsampling: a 2-week query at 60 s resolution is ~20k points/metric — never ship that; default `step` scales with range. Raw resolution requires explicitly small windows.
- The group enum + per-group name errors make this tool self-teaching: a wrong guess returns the valid vocabulary for exactly one group, not all 74 names.
- **The metric-group enum is the canonical owner of `baseline_class`** — the server-side attribute deciding whether `self_baseline` is a valid reference frame for a group. It is not model-visible and costs no def tokens here; the assignments table and its rationale live in [`02-analyze_window.md`](02-analyze_window.md#reference-window-validity-baseline_class).

## Errors

Unknown metric in group → actionable (valid names for that group), `retryable: true` (with corrected name). Range too large → suggests `step` or narrower window. Site lacks group → `not_collected`, suggests `get_monitor_status` for coverage.

**Def-token target: 220.**

## Open questions

- Exact group→metric mapping table (build-time, from the sibling TowerWatch repo's
  `docs/metrics-inventory.md` — the domain source of truth; not duplicated here).
- Max range and default page size — set after seeing real payload sizes in fixture.
