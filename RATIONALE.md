# Rationale

Append-only. One dated entry per deliberate choice a reviewer would otherwise
report as a defect. Newest at the bottom.

An ADR holds a direction-setting decision; this file holds its code-visible
residue -- the line a reviewer flags on sight. When a review finding is refuted
and the reason would apply again, it becomes an entry here.

---

2026-08-22 - `tool_span` passes `record_exception=False` and `set_status_on_exception=False`,
  discarding stack traces on every error.
  OTel's defaults attach an `exception` event with message and full trace, and fill
  the status description with the exception type plus message -- both route around
  the `SpanMetrics` TypedDict whitelist that structurally enforces the no-secrets
  invariant. Exception messages here do carry payload-shaped data
  (`UnknownMetricError` lists a group's metric names). The error *class* is still
  recorded and status is still set to ERROR below.
  Source: src/towerwatch_ops_agent/telemetry/spans.py:76-88
  Reviewers report: "disabling exception recording destroys debuggability -- remove these two arguments."

2026-08-22 - Enum rationale lives in `#` comments above the class, and a test enforces
  docstrings stay under 120 chars.
  Pydantic copies a class `__doc__` verbatim into the JSON Schema, so a docstring here
  ships maintainer notes to the model on every call. `MetricGroup`'s ~750-char
  rationale measured 29% of the rendered request schema.
  `test_enum_docstrings_stay_out_of_the_schema` makes the convention a build break
  rather than a habit.
  Source: src/towerwatch_ops_agent/domain/models.py:22-25; tests/domain/test_models.py:32-51
  Reviewers report: "missing docstrings on public enums; a test asserting a doc-length ceiling is a
  bizarre anti-documentation check."

2026-08-22 - `MetricGroup` is hardcoded while `Site` is derived at startup.
  ADR-0007 names `section`, `site`, and `event_types` as the derived enums --
  `metric_group` is deliberately not one. TowerWatch's `metrics-inventory.md` has ten
  section headings that do not map onto these eleven values; `signal`,
  `cell_identity`, and `hardware` are all carved out of its single "Cellular radio"
  section, so there is no source to derive from. The split is an editorial judgment
  about what an agent should be able to ask for.
  Source: src/towerwatch_ops_agent/domain/models.py:13-20; ADR-0007
  Reviewers report: "inconsistent enum construction -- `MetricGroup` violates ADR-0007's
  derive-don't-hardcode rule."

2026-08-22 - `query_metrics` catches bare `Exception` with a `noqa`, and response construction
  sits inside the try rather than in an `else:`.
  The error contract requires every tool to return an actionable envelope carrying
  `data_status`, so no failure may escape as an exception. The `else:` placement was a
  real shipped bug: `SeriesPoint` is an unvalidated dataclass, so a live client can
  hand back a sample Pydantic rejects, which raised out with no `data_status` at all.
  Source: src/towerwatch_ops_agent/tools/query_metrics.py:172-185; regression test
  tests/tools/test_query_metrics.py:253-262; commit 04a4e9d
  Reviewers report: "broad `except Exception` swallows everything -- narrow it, and move response
  construction into an `else:` block."

2026-08-22 - Internal error messages are replaced with the exception class name only, dropping
  the exception text from the tool result.
  The exception text on an arbitrary failure carries whatever the raising code put
  there -- a `FileNotFoundError` names the server's filesystem path -- and the binding
  invariant is that internals never appear in a tool result. The class is enough for
  the model to know retrying will not help; details go to the operator's log and the
  span's `tool.error_type`.
  Source: src/towerwatch_ops_agent/tools/query_metrics.py:259-274, :207-225; commit 3731143
  Reviewers report: "error messages are uselessly generic -- include the underlying exception text."

2026-08-22 - `FixtureClient.get_metric_series` raises `ValueError` on a `page_token` past the
  end instead of returning an empty page.
  A token past the end would otherwise return `ok` with zero points and no coverage
  note -- "success, here is nothing" -- which a model reads as absence of data rather
  than a bad request. Emptiness may never look like an answer in this envelope.
  Source: src/towerwatch_ops_agent/domain/fixture_client.py:175-185; advice branch at
  src/towerwatch_ops_agent/tools/query_metrics.py:239-248
  Reviewers report: "pagination should terminate gracefully -- raising on an over-run offset is a bug."

2026-08-22 - A `not_collected` verdict is computed across every window for a site, not from the
  first window that declares the group absent.
  A site whose probe was offline for one window but collecting in another does collect
  the group. Returning `not_collected` there would claim "no evidence" while evidence
  sits in the corpus. Reasons are read from documented `groups_absent` data, never
  inferred from an empty result -- that is what keeps `not_collected` distinct from
  `empty_window`.
  Source: src/towerwatch_ops_agent/domain/fixture_client.py:103-111; enforced at
  src/towerwatch_ops_agent/domain/protocol.py:67-96
  Reviewers report: "inefficient full scan where an early return on the first absent match would do."

2026-08-22 - The server defaults to fixture mode and raises `NotImplementedError` for live mode.
  Live mode needs a `GrafanaCloudClient` that does not exist yet (ADR-0002 defines both
  implementations; only `FixtureClient` has landed). Defaulting to live would fail at
  startup rather than serve. Tests and evals are authoritative against the fixture
  anyway, for determinism.
  Source: src/towerwatch_ops_agent/config.py:28-29; src/towerwatch_ops_agent/server.py:33-37
  Reviewers report: "server ships defaulting to test data -- a production deploy would silently serve
  fixtures."

2026-08-22 - `FixtureClient` freezes `now()` to the manifest's `fixture_now` for the whole
  process.
  A clock that drifts mid-session would make two identical eval runs disagree, which is
  the entire thing the fixture exists to prevent (ADR-0002: determinism is the Phase 2
  gate). Both modes resolve "now" through the same `DataClient.now()` seam --
  deliberately on the client rather than a separate injected Clock, so there is one
  seam per mode instead of two.
  Source: src/towerwatch_ops_agent/domain/fixture_client.py:54-57, :68-70;
  src/towerwatch_ops_agent/domain/protocol.py:123-129
  Reviewers report: "`now()` returns a hardcoded past timestamp -- a stale cached value that should read
  the system clock."

2026-08-22 - `downsample` averages each bucket rather than taking the last sample, and anchors
  buckets to the window start.
  A bucket's last sample discards everything else in it, silently erasing exactly the
  spikes that matter on network data. Anchoring to `origin` means the same request
  always produces the same bucket boundaries -- eval stability depends on it.
  Source: src/towerwatch_ops_agent/domain/windows.py:74-81
  Reviewers report: "downsampling should use last-value (Prometheus/Grafana convention) -- averaging
  distorts the series."

2026-08-22 - The request annotation on the query tool is set at runtime instead of written in
  the function signature.
  `server.py` uses `from __future__ import annotations`, so a written annotation would
  be a string that FastMCP cannot resolve -- the request model is a local built at
  startup from the derived site enum (ADR-0007), not a module-level name.
  Source: src/towerwatch_ops_agent/server.py:62-66
  Reviewers report: "runtime annotation mutation is a hack -- just annotate the parameter properly."

2026-08-22 - Two slots are wired but permanently inert: the retry attribute always reads false,
  and `resolve_window` accepts only absolute timestamps.
  Deciding whether a call is a retry needs task-scoped history, which is
  server-middleware state a per-call context manager has no business keeping -- so the
  SLI reads a flat 0% until that lands elsewhere. Separately, no contract doc defines a
  relative time grammar, so none was invented; absolute windows still route through the
  clock seam so the call site is real and tested.
  Source: src/towerwatch_ops_agent/telemetry/spans.py:51-57;
  src/towerwatch_ops_agent/domain/windows.py:40-44
  Reviewers report: "dead code -- delete the clock seam and the retry attribute."

2026-08-22 - The `DataClient` Protocol declares only `get_metric_series` and `now`, one method
  against seven planned tools.
  The Protocol grows one method per tool as tools are built, rather than being
  speculatively drafted for all seven -- the group-to-layer mapping the later tools need
  does not exist yet. It was landed *before* either implementation, so the seam existed
  before anything could be written against a concrete class.
  Source: src/towerwatch_ops_agent/domain/protocol.py:103-106, :7-9
  Reviewers report: "incomplete interface -- missing methods for six of the seven documented tools."

2026-08-22 - There is no `run_probe` tool and no `diagnose_symptom` tool despite both appearing
  in the Phase 1 candidate table.
  `run_probe` was cut because TowerWatch's 60-second collection loop already probes
  continuously, bounding an on-demand probe's marginal value at one minute of freshness
  -- and keeping the surface read-only except `run_speedtest` means exactly one
  meaningful host approval gate. `diagnose_symptom` was cut because diagnosis is
  irreducibly open-context reasoning and the binding invariant forbids LLM calls inside
  the server; it ships as the `diagnose-rca` skill.
  Source: ADR-0003; ADR-0008
  Reviewers report: "the spec lists `run_probe` and `diagnose_symptom` but neither exists -- incomplete
  tool surface."

2026-08-22 - The runbook is served by a keyed section-enum lookup with no embeddings, vector
  store, or chunking.
  The corpus is one bounded ~9KB document with ~13 symptom-indexed headings that a human
  already curated as the symptom-to-procedure index. RAG is rejected on cost/benefit at
  this size, explicitly not on principle -- Phase 3 measures semantic retrieval against
  this as the baseline. Content is returned verbatim and never summarized server-side,
  because an operator sometimes needs the exact command.
  Source: ADR-0006
  Reviewers report: "no retrieval layer -- this should use embeddings," and "returning content verbatim
  is an injection surface."

2026-08-22 - CI runs on every PR branch head with a not-cancelled condition on each step, so
  lint, format, typecheck, and test never short-circuit each other.
  Branch-level gating caught a real defect: PR #3's telemetry tests imported the tool
  layer from PR #4, so the branch was red checked out alone while the suite passed at
  the top of the stack. Non-short-circuiting steps exist because a type error and a
  failing test are independent findings, and seeing only the first costs a round trip.
  Source: .github/workflows/ci.yml:1-7, :36-38; commits dc19db9, 2f610f1
  Reviewers report: "the per-step not-cancelled condition wastes CI minutes -- use fail-fast."
