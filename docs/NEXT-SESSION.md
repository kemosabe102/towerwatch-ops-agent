# Next session — handoff

*Written 2026-08-21, at the end of the session that landed slice one. Delete this file
once its contents are absorbed; it is a handoff note, not a permanent doc.*

## Where things actually stand

**One of seven tools is built and the server runs.** `query_metrics` works end to end
over a real MCP client session against a stub fixture. 95 tests, ruff/format/pyright
clean, CI green on every PR.

**PRs #1–#4 are merged but PR #5 was still open when this was written.** Verify before
anything else: `gh pr view 5 --json state`. `main` carries only PR #1's contract layer
until #5 lands — no `server.py`, no tool, no fixture client. #2–#4 merged into their
parent branches instead of `main` (see Process notes), and #5 is the fix.

**Before reasoning about anything below:** confirm PR #5 merged, then run
`uv run pytest -q` and confirm 95 passed. If either fails, that is the first job.

**The approved plan for the next phase lives in `~/.claude/plans/` —**
`contracts-are-locked-and-staged-starfish.md`. Read it first. It supersedes the ordering
in "What to work on next" below, which is kept only for the background detail it carries.

### The one-line status

| Piece | State |
|---|---|
| `query_metrics` | built, tested, runs |
| Other six tools | not started |
| Fixture corpus | 2-window hand-authored **stub** — not the real corpus |
| SLI dashboard | nothing exported; no OTel exporter wired |
| Eval harness (Phase 2) | not started |
| Router / retrieval (Phase 3) | not started |

## Phase 1 acceptance criteria — the real gate list

From `docs/specs/spec-phase1-mcp-server.md`. **None are met.** These are the stateless
gates that decide whether Phase 1 is done; do not declare it complete without each one
independently checkable.

- [ ] All tools pass MCP Inspector interactively
- [ ] Spans visible in Grafana for a scripted 20-call session; SLI dashboard screenshot committed
- [ ] `def_tokens.md` exists and total ≤ budget (or documents the overage decision)
- [ ] `bench.md` exists with all cells filled
- [ ] `CLAUDE.md` + README with architecture diagram committed

## What to work on next, in order

> **Superseded by the plan.** The plan measures all seven defs up front against stub
> handlers, because the ≤1,200 gate is a *total* and cannot be judged from one tool. The
> per-item notes below still hold as background.

### 1. Def-token measurement — blocked on you, ~1 minute once unblocked

`scripts/measure_def_tokens.py` has **never run**. It needs `ANTHROPIC_API_KEY`.

The PR #1 fix cut the request schema from 2548 to 1783 characters, which is real, but a
bytes/4 estimate overcounts JSON schema badly — it is not a measurement and was never
reported as one. Target is 220 tokens.

Set the key, run the script, commit `def_tokens.md`. That closes a Phase 1 gate outright.

### 2. The real fixture corpus

The current corpus is a deliberate stub: two windows, hand-authored, proving the format
and the code path only. The real one is a transform over data that **already exists and
is committed**:

    ../towerwatch/data-archive/standstill-jul2026/jul01_15_throttle/
    40 CSVs, 22MB, 60s resolution, real July 2026 incident window

Settled already, do not relitigate:
- `provenance: exported` — verified against
  `../towerwatch/docs/standstill-throughput-evidence-jul2026.md:10`: "exported to CSV
  before Grafana Cloud's 14-day retention expired." An earlier draft of this note said
  `reconstructed`; that was wrong. The data was pulled while still in retention, so the
  provenance chain is direct, not rebuilt from an evidence pack.
- `pseudonym_scheme: none_required` — audited all 40 CSVs, zero IPs, zero hostnames.
  Pseudonymising already-public data would create a mapping to protect, i.e. a secret
  where none existed.
- The answer key is committed **in its own commit, before any eval runs**

**Now decided:** the series file format. The doc said to decide after seeing real payload
sizes — measured at **529,467 rows / 22MB across 40 CSVs**, which is not a git artifact at
full resolution. Decision: keep the stub's JSON shape, commit **trimmed** curated windows.
Readable fixtures matter because the answer key must be auditable by eye; the full archive
stays in `towerwatch` as provenance.

### 3. `analyze_window` — NOT tool #2; see the plan

The plan builds `get_runbook` and `compare` first, then `analyze_window` third — it is the
*most* blocked tool, with five open design questions, no threshold table, and no
group→layer mapping. `compare` also builds the percentile helpers it needs.

The most interesting tool in the design and currently only prose. It is where
`baseline_class` and reference-frame validity become code — the ideas the whole contract
layer was built to express.

Contract: `docs/design/02-analyze_window.md`. Note `baseline_class`
(`contention_sensitive` | `device_local`) is a **server-side registry attribute and is
not model-visible**.

### 4. OTel exporter + the SLI dashboard

Spans are emitted but go nowhere — there is no exporter configured. The gate needs a
scripted 20-call session visible in Grafana plus a committed screenshot.

**Known gap:** the retry-rate SLI is defined in `09-observability-spans.md` and
`tool.retry` is its slot, but nothing computes it. It needs task-scoped middleware state
("has this tool already errored under this `task.id`") — a per-call context manager has
no business keeping a call log. There is a `TODO(retry-sli)` in `telemetry/spans.py`.
Until it is fed, that SLI reads a flat 0%.

## The pattern worth carrying forward

Five real bugs were found across the four PRs. **Four shared one shape: correct only
because a single disciplined implementation was the only caller.**

- absence logic returned `not_collected` while evidence sat in the corpus
- OTel's `record_exception` default leaked exception messages around the span whitelist
- the response envelope could contradict its own `data_status`
- a malformed sample escaped the envelope entirely, returning no `data_status` at all

Every one of them would have surfaced the day `GrafanaCloudClient` lands. **That is an
argument for writing the live client sooner rather than later** — a second implementation
is what actually tests whether a seam is a seam. It is not currently scheduled for
Phase 1; worth deciding whether it should be.

## Process notes that cost time this session

- **Merge stacked PRs one at a time and wait for the retarget.** Merging four in 47
  seconds left #2–#4 merged into their parent branches instead of `main`, needing a fifth
  PR to fix. GitHub retargets a child only *after* its parent merges.
- **GitHub does not allow self-approval.** Branch protection now requires a PR with
  `enforce_admins: true` but **0 approving reviews** — the approval click was a proxy for
  reading that GitHub would never let a solo author make. Direct pushes to `main` are
  still blocked for everyone.
- **Gate each branch standalone**, not just at the tip of a stack. PR #3 was red on its
  own branch and nobody noticed, because the suite only passed at the top.

## Cleanup still owed

- [ ] Delete merged branches: `pr1-contracts`, `pr2-fixture-client`, `pr3-telemetry`,
      `pr4-tool-and-server`, `slice-one-query-metrics`
- [ ] Update README **Status** — it still says "implementation not started", which is now
      false. It is the authoritative present-vs-deferred list per `CLAUDE.md`.
- [ ] Delete this file once absorbed into the plan
