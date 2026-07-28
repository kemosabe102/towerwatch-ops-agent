# Fixture manifest — the curated corpus and its answer key

The fixture is **a curated, documented export — not a capture**. Each window is exported
deliberately, with its expected findings recorded before any agent sees it. The manifest
is that record: it describes what the corpus contains, where each window came from, and
what a correct reading of it looks like.

This answers the format question left open in
[ADR-0002](../adr/0002-dual-mode-data-access-via-protocol.md) (*"fixture curation — which
windows, which sites, what format"*), which is the implementation-blocking input before
the first code slice.

## Why a manifest rather than a directory of files

A dump is opaque — a reader cannot tell what scenario it encodes, which is the same
objection that killed HTTP cassettes in ADR-0002. Three properties need a written record:

- **Provenance** — whether a window is real, rebuilt, or authored. Unlabeled synthetic
  data silently converts the eval corpus from *"did the agent diagnose a real incident"*
  into *"did the agent find the anomaly I planted."* Those measure different things.
- **The frozen clock** — `fixture_now` has to live somewhere the server reads at startup.
- **The answer key** — the documented reading has to exist before agent output is seen.

## Top-level fields

| Field | Type | Notes |
|---|---|---|
| `fixture_now` | ISO-8601 | the frozen clock; the fixture-mode source for the seam in [`00-contract-conventions.md`](00-contract-conventions.md) |
| `generated_at` | ISO-8601 | when the corpus was built (distinct from `fixture_now`) |
| `windows` | list | one record per exported window, below |
| `pseudonym_scheme` | str | names the scheme; **never** the mapping — see Scrub |

## Window records

| Field | Type | Notes |
|---|---|---|
| `id` | str | stable handle referenced by eval cases |
| `site` | enum | `standstill` \| `home`, per the derived site enum |
| `start`, `end` | ISO-8601 | explicit offset, per conventions |
| `role` | enum | `incident` \| `reference` \| `boundary` — a *kind*, not a slot; multiple windows may share a role |
| `provenance` | enum | `exported` \| `reconstructed` \| `synthetic` — **mandatory** |
| `resolution` | str | a `query_metrics` `step` value (`60s`, `1d`) — same vocabulary, so fixture and live downsampling agree |
| `payload` | str | path to this window's series file, relative to the manifest |
| `groups_present` | list[enum] | `metric_group` values from [`01-query_metrics.md`](01-query_metrics.md) — that enum is the vocabulary here and everywhere below |
| `groups_absent` | list[{`group`, `reason`}] | **deliberate** absences, each with its reason — sparse coverage is tested here |
| `expected_findings` | object | the answer key; see below |

`role` carries meaning the naming has to keep honest: a `reference` window is a quiet,
non-holiday period used for contrast — it is **not** a steady-state baseline. The site is
seasonal and occupancy-driven, so no window at this scale represents "normal." Calling it
a reference rather than a baseline is the whole point (see
[`02-analyze_window.md`](02-analyze_window.md), reference-window validity).

### Provenance values

- **`exported`** — pulled from live Grafana Cloud while the window was still inside
  retention.
- **`reconstructed`** — rebuilt from the evidence pack's exported numbers after the raw
  window aged out. Not a downgrade: it documents a provenance chain (real incident →
  exported analysis → fixture seeded from it) and demonstrates designing around a known
  retention constraint.
- **`synthetic`** — authored. Permitted, but never silently: the field's purpose is that
  `synthetic` cannot be forgotten, not that it is forbidden.

Because provenance is a field value rather than a deadline, retention no longer runs a
clock on curation. Whether the July window is `exported` or `reconstructed` changes one
label.

## Expected findings — the answer key

Each window records the reading the curator verified by hand: which layers degraded, the
key numbers, and the causal ordering. This is the answer key that eval cases score
against, so its timing is load-bearing.

Curate to this shape — whether the numeric parts harden into a strict schema is open
(below), but two curators must not invent different layouts:

```yaml
expected_findings:
  overall: degraded
  layers:                        # only layers with a non-trivial reading
    throughput: {status: bad, key_numbers: {p50_mbps: 4.1, baseline_p50_mbps: 47.3}}
    signal:     {status: good, note: "RSRP steady — rules out propagation"}
  causal_order: [throughput, wan] # earliest-affected first; [] if not established
  verdict: >
    One-paragraph prose reading. The rubric scores against this.
```

- **Committed before any eval executes**, in its own commit. Once agent output has been
  observed, a curator's sense of what a window "obviously shows" drifts toward what the
  agent said.
- **The harness logs the manifest commit SHA it scored against.** Git already makes an
  edit a diff; what this adds is provenance binding — a result is always traceable to the
  key in force when it ran, and a key edited afterward surfaces as a version mismatch
  rather than a memory. No hashing machinery.

Eval-side rules for consuming this key — including the positive-control pairing that
`insufficient_evidence` cases require — are in [`11-eval-design.md`](11-eval-design.md).

## Resolution and the rollup section

Full 60 s resolution ships **only inside incident and reference windows**. Surrounding
context ships as daily per-metric rollups: `count`, `mean`, `p50`, `p95`, `p99`, `max`.

Two reasons. Committability: 13 days of trailing history at 60 s across the metric
inventory and two sites is millions of points — not a git artifact. And the rollup uses
the **baseline ledger's own schema** from
[ADR-0009](../adr/0009-baseline-reference-data-beyond-retention.md), so the fixture
exercises that format before the ledger is built.

State it plainly in the corpus: **the rollup is context, not a steady-state baseline.**

## Scrub

The fixture is real home-network telemetry, and it is the file least likely to be read
before it is committed. Public IPs, resolver addresses identifying the ISP, coarse
geolocation implied by carrier and band and site name, uptime patterns describing when a
house is occupied — none catastrophic alone, all permanent once pushed.

- Hostnames and IPs are rewritten to **stable pseudonyms by the generation script**, not
  by judgment at commit time. A manual scrub eventually gets skipped.
- **Deterministic pseudonyms, not redaction** — records must stay comparable across the
  corpus or the analysis means nothing.
- The mapping is **never committed**. The manifest names the scheme only.

## Window set

| Role | Window | Notes |
|---|---|---|
| `incident` | the July throughput degradation | provenance per what retention allows at export time |
| `reference` | a quiet non-holiday weekend | contrast, not baseline |
| `boundary` | an `anchored_trend` request reaching past fixture history | the `insufficient_evidence` case |

The `boundary` case needs no additional data — it is a request that exceeds
`history_available`, and [`02-analyze_window.md`](02-analyze_window.md) already specifies
that behavior, so it is a *request against* the existing corpus rather than a fourth
export.

**Sparse coverage rides on the `incident` window**, not a separate one: the `home` site
lacks the `signal` and `hardware` groups entirely (no cellular modem — those metrics are
standstill-only), so `groups_absent` on the home-site record carries them with the reason
`not_collected_at_site`. That exercises the same code path a missing host would, at no
extra curation cost. The phone host stays out of the corpus — phone collection only
happens during rare on-site visits.

## Open questions

- Series-file format and internal layout — the manifest fixes *where* a window's payload
  lives (`payload`, one file per window) but not what's inside it. Decide after seeing real
  payload sizes, which also gates `query_metrics`' max range and default page size
  ([`01-query_metrics.md`](01-query_metrics.md)).
- Whether `expected_findings` hardens into a schema strict enough for programmatic checks,
  or the numeric parts stay loose. Phase 2's programmatic-checks-first rule pushes toward
  strict for `key_numbers`, rubric-scored for `verdict`. The shape above is the floor
  either way.
