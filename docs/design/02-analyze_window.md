# towerwatch_analyze_window

**Purpose:** server-side judgment over a time window — the interpretive core. Returns a layered health breakdown scored against explicit reference frames. All computation deterministic; no LLM inside.

**Selection sentence:** *Pick me when you want an assessment of a window — was it healthy, what degraded, relative to what — and you don't need the underlying rows.*

## Inputs

| Param | Type | Constraints / notes | Example |
|---|---|---|---|
| `site` | enum | required | `"standstill"` |
| `start`, `end` | ISO-8601 | required; max range enforced | — |
| `frames` | list[enum], optional | `self_baseline` \| `type_profile` \| `anchored_trend`; default: all applicable | `["self_baseline"]` |
| `focus` | enum, optional | limit to one metric_group for a cheaper, deeper read | `"signal"` |

## Response

Layered breakdown — one block per layer, each with `status` (`good` / `degraded` / `bad` / `insufficient_evidence`), key numbers, and per-frame deltas:

1. `gateway` (inside-the-walls health: gateway RTT/HTTP, clients)
2. `dns` (per-resolver timings; carrier-resolver vs public split)
3. `wan` (RTT/jitter/loss per target, TCP connect)
4. `throughput` (HTTP samples, speedtests, bufferbloat deltas)
5. `signal` (RSRP/RSRQ/SINR, band, CA state — where collected)
6. `hardware` (temperature, thermal state, eth speed, modem uptime — where collected)

Plus: `overall` roll-up, `frames_applied` (with each frame's reference values — so the model can *explain* the judgment), `data_status`, `coverage_notes`.

## Reference frames (the multi-connection-type answer, encoded)

| Frame | Computes | Catches | Blind spot |
|---|---|---|---|
| `self_baseline` | window vs site's trailing N-day percentiles | change ("worse than its own normal") | normalizes slow drift & chronic badness |
| `type_profile` | window vs per-connection-type profile (config) | absolute inadequacy ("bad *for cable*") | site-specific legitimate variance |
| `anchored_trend` | window vs fixed anchor period + long-window slope | slow creep (the 1%/week failure) | needs history; anchor choice is a config decision |

The model chooses which frame answers the user's question; the server computes all requested frames honestly, including disagreement between them.

## Design notes

- The layered breakdown is the **localization substrate**: gateway-good + wan-bad ⇒ ISP side; gateway-bad ⇒ inside the walls. The layers make that inference one step for the model.
- `insufficient_evidence` is a legal per-layer status (sparse-coverage rule) — a site without hardware metrics shows `hardware: insufficient_evidence (not_collected)`, never `good`.

## Retention constraint (binding — Anthony, 2026-07-24)

The environment retains **~2 weeks** of queryable data. Consequences, designed in rather than discovered:

- `self_baseline` trailing window ≤ ~13 d (fits retention).
- `anchored_trend` **cannot see past retention from live queries** — months-scale slow drift is undetectable without persisted history. Every frame response reports `history_available` honestly; a request exceeding it returns `insufficient_evidence` for that frame, never a silently-shortened answer.
- The fix is a **baseline ledger**: daily per-metric rollup aggregates (count/mean/p50/p95/p99/max) persisted by the server to a tiny local store (JSON/SQLite), appended on a schedule — classic downsampled-retention-tier thinking at hobby scale. Recommendation: design the frame API to consume it now, build the ledger as a fast-follow after the Phase 1 gate (two-way door; also listed in production-path as "what a real deployment does with Mimir/Thanos-style downsampling").

## Errors

Window precedes available history → actionable (earliest available + which frames still apply). Frame inapplicable (no type profile configured) → frame omitted + noted, not an error.

**Def-token target: 250** (largest def — it carries the frame vocabulary).

## Open questions

- Trailing-baseline window length within retention; anchor period once the ledger exists — config decisions, ADR-worthy.
- Threshold table per connection type — seed from TowerWatch history + published norms; mark provisional.
- Ledger build timing (post-Phase-1 recommended) and whether TowerWatch or the MCP server owns the rollup job.
