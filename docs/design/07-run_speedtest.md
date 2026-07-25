# towerwatch_run_speedtest

**Purpose:** the sole actuator — trigger the Cloudflare adaptive speedtest on a site's Pi, for troubleshooting an active issue. Costly (~550 MB/run on a 30 GB/month budget), so guarded in code and gated by the host.

**Selection sentence:** *Pick me only when a fresh throughput measurement is needed right now to investigate an active issue — recent scheduled results (via `query_metrics`, group `speedtest`) are usually enough.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `site` | enum | required | `"standstill"` |
| `reason` | str | required, logged + attached as the run's `triggered_by` context — makes every manual run auditable | `"investigating slow-Wi-Fi complaint"` |

## Guards (server-side, deterministic — the model is never asked to remember)

1. **Budget guard:** refuse if month-to-date bytes + worst-case run cost threaten the 30 GB cap.
2. **Rate guard:** minimum interval between manual runs; max N manual runs/day (config).
3. Refusals are actionable: current usage, cap, projected reset date, and the suggested alternative (recent scheduled results).

**Annotation:** non-read-only → host approval gate fires before execution (the human approves spending 550 MB). Idempotent: no; destructive: no.

## Response (server-composed before/after context — decision #5)

- `result`: download/upload Mbps, bytes used, duration
- `pre`: compact status snapshot before the run (freshness, current signal state)
- `during`: concurrent radio metrics captured across the run window (the 60 s loop was already collecting — signal state *during* saturation is diagnostic gold: thermal, CA, band)
- `budget_after`: month-to-date + pace (the third budget surface)
- `data_status` per conventions

One call returns an interpretation-ready package; the agent keeps the open judgment — whether the package warrants digging further.

## Fixture mode

Stubbed: returns a canned result clearly marked `fixture: true`, exercising the full response shape (so evals can cover the tool without spending bytes or needing tailnet reach).

## Deployment constraint (honest note)

Live mode requires the MCP server to have tailnet reach + SSH identity for the Pis — it runs on a tailnet member (dev machine or always-on host). Secrets stay server-side per the intent/privilege boundary. Production path: gateway-fronted always-on deployment (see production-path doc).

## Errors

`budget_exceeded` (non-retryable until reset; full accounting included) · `rate_limited` (`retry_after_s`) · `site_unreachable` (non-retryable; suggests `get_monitor_status` + runbook `silent-pi`) · `fixture_mode` distinction per above.

**Def-token target: 150.**

## Open questions

- Should `reason` feed the Grafana `triggered_by` label as `agent:<reason>`? Lean yes — dashboard-visible audit trail for free.
