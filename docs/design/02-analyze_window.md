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

`frames_applied` is **not uniform across layers**: `self_baseline` entries for
contention-sensitive layers carry an additional `reference_composition` note. The shape is
conditional on the layer's `baseline_class` — see [Reference-window validity](#reference-window-validity-baseline_class) below before building the response schema.

## Reference frames (the multi-connection-type answer, encoded)

| Frame | Computes | Catches | Blind spot |
|---|---|---|---|
| `self_baseline` | window vs site's trailing N-day percentiles | change ("worse than its own normal") | normalizes slow drift & chronic badness; **baseline validity is per-group, not global** — see below |
| `type_profile` | window vs per-connection-type profile (config) | absolute inadequacy ("bad *for cable*") | site-specific legitimate variance |
| `anchored_trend` | window vs fixed anchor period + long-window slope | slow creep (the 1%/week failure) | needs history; anchor choice is a config decision |

The model chooses which frame answers the user's question; the server computes all requested frames honestly, including disagreement between them.

### Reference-window validity (`baseline_class`)

`self_baseline` compares a window against the site's own recent past. That reference is
only meaningful for signals whose recent past represents a comparable state — and at a
rural, occupancy-driven site, some signals fail that test. Load at standstill tracks how
many people are physically out there, and the site is seasonal on top of that, so a
trailing window is a *reference period*, not a steady state.

This is a correctness property, not a fixture inconvenience: a frame that returns a
confident verdict on a contention-sensitive signal against an occupancy-mismatched
reference will attribute a busy-weekend degradation to hardware or propagation.

**Mechanism:** each metric group carries a `baseline_class` attribute — `contention_sensitive`
or `device_local` — in the server-side registry. It is **not model-visible vocabulary and
not a third taxonomy**: no def-token cost, nothing for the model to learn or misselect
against. The frame logic reads it; the model sees only the resulting caveat.

**Canonical owner:** `baseline_class` attaches to the `metric_group` enum in
[`01-query_metrics.md`](01-query_metrics.md), which is the registry that owns metric
definitions. The layers above inherit it through the group→layer mapping.

**Assignments are provisional** — each is an empirical claim about this site and this
carrier, and none has been measured. Every assignment records a one-line physical
mechanism; one that cannot be justified in a sentence was guessed. Falsification path:
correlate each group against an occupancy proxy (weekday/weekend, holiday/ordinary) and
reclassify what disagrees.

| Group | Class | Physical mechanism |
|---|---|---|
| `throughput`, `speedtest` | `contention_sensitive` | shared-cell capacity divided among active users |
| `bufferbloat` | `contention_sensitive` | latency under load; queue depth rises with cell utilization |
| `latency`, `tcp` | `contention_sensitive` | queueing delay on the shared path rises with load |
| `signal` — SINR | `contention_sensitive` | the interference term is other transmitters by definition (`m6_sinr`, "signal-to-interference-plus-noise") |
| `signal` — RSRQ | `contention_sensitive` | derived as RSRP over RSSI; RSSI is total wideband received power, so it rises with other users' traffic on the band even when RSRP holds |
| `signal` — RSRP | `device_local` | received power from the serving beam — distance, obstruction, antenna |
| `signal` — `m6_bars`, `m6_radio_quality` | `contention_sensitive` | device composite scores that fold RSRQ/SINR in; classify with their most load-sensitive input |
| `signal` — `m6_rx_level`, `m6_tx_level` | `device_local` | uplink/downlink power levels — antenna and path geometry (TowerWatch reads `m6_tx_level` as an antenna-experiment signal) |
| `hardware` | `device_local` | chassis thermal, eth speed, modem uptime — ambient temperature and the device |
| `gateway` | `device_local` | LAN-side; local client count doesn't track tower occupancy |
| `dns` | `device_local` | resolver round-trip, not shared-spectrum capacity |
| `cell_identity` | `device_local` | band, PCI, cell ID, CA state — serving-cell identity, not load |
| `meta` | *n/a* | collection-process metrics, not health signals — excluded from `self_baseline` rather than classified |

The `signal` group splits internally, so `baseline_class` is per-metric within it rather
than one value for the whole group. The 5G NR and per-band-tagged variants
(`m6_nr5g_*`, `m6_sig_*`) inherit from their base quantity — the mechanism is the same
under NR as under LTE.

**Response consequence:** `contention_sensitive` layers carry a `reference_composition`
note in `frames_applied`, stating what the trailing window actually spanned — a holiday, a
summer weekend, an occupancy-driven period. `device_local` layers report the delta plain.

## Design notes

- The layered breakdown is the **localization substrate**: gateway-good + wan-bad ⇒ ISP side; gateway-bad ⇒ inside the walls. The layers make that inference one step for the model.
- `insufficient_evidence` is a legal per-layer status (sparse-coverage rule) — a site without hardware metrics shows `hardware: insufficient_evidence (not_collected)`, never `good`.

## Retention constraint (binding — Anthony, 2026-07-24)

The environment retains **~2 weeks** of queryable data. Consequences, designed in rather than discovered:

- `self_baseline` trailing window ≤ ~13 d (fits retention). **Fitting retention is not the
  same as being a baseline** — 13 days of a seasonal, occupancy-driven site is a reference
  period, not a steady state. See reference-window validity above; the two constraints are
  independent and both bind.
- `anchored_trend` **cannot see past retention from live queries** — months-scale slow drift is undetectable without persisted history. Every frame response reports `history_available` honestly; a request exceeding it returns `insufficient_evidence` for that frame, never a silently-shortened answer.
- The fix is a **baseline ledger**: daily per-metric rollup aggregates (count/mean/p50/p95/p99/max) persisted by the server to a tiny local store (JSON/SQLite), appended on a schedule — classic downsampled-retention-tier thinking at hobby scale. Recommendation: design the frame API to consume it now, build the ledger as a fast-follow after the Phase 1 gate (two-way door; also listed in production-path as "what a real deployment does with Mimir/Thanos-style downsampling").

## Errors

Window precedes available history → actionable (earliest available + which frames still apply). Frame inapplicable (no type profile configured) → frame omitted + noted, not an error.

**Def-token target: 250** (largest def — it carries the frame vocabulary).

## Open questions

- Trailing-baseline window length within retention; anchor period once the ledger exists — config decisions, ADR-worthy.
- Whether `reference_composition` is **computed** (server derives what the trailing window spanned) or **configured** (a calendar of known-atypical periods). Recommend computed — it needs no maintenance and cannot go stale.
- `baseline_class` assignments are provisional until measured against an occupancy proxy. The correlation experiment is a Phase 2/3 result, not a Phase 1 gate.
- Threshold table per connection type — seed from TowerWatch history + published norms; mark provisional.
- Ledger build timing (post-Phase-1 recommended) and whether TowerWatch or the MCP server owns the rollup job.
