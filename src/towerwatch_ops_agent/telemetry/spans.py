"""One span per tool call (`docs/design/09-observability-spans.md`).

The no-secrets invariant is closed at type-check time rather than by a runtime filter.
`tool_span` never receives a request or response object — only the primitives a caller
writes into a `SpanMetrics` TypedDict whose keys pyright fixes. A filter would need
maintaining forever as new fields appear; a closed key set needs nothing maintained.

Two honest limits on that, worth knowing before trusting it:

- TypedDict keys are erased at runtime, so the control is pyright in CI, not the
  interpreter. A `cast(SpanMetrics, ...)` or a `# type: ignore[literal-required]` at an
  assignment site defeats it in one line that no other tooling flags. Treat either as a
  red flag in review here specifically.
- It covers the metrics dict only. `site`, `task_id`, `session_id` and `model` are
  plain `str | None` parameters written verbatim. `site` is safe by construction — it
  comes from a closed enum — but nothing constrains the other three, and the span
  schema means them as opaque correlation ids. Whatever populates them in Phase 2 owes
  that check; this module cannot make it for them.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TypedDict

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("towerwatch_ops_agent")

SPAN_NAME = "towerwatch.tool_call"


class SpanMetrics(TypedDict, total=False):
    """Values a tool may attach to its span. Sizes and classes only — never contents.

    Adding a key here is the deliberate act that lets a value reach telemetry; pyright
    rejects any key not listed, which is the structural half of the no-secrets rule.
    """

    data_status: str
    input_bytes: int
    output_bytes: int
    page_index: int
    retry: bool
    error_type: str


# TODO(retry-sli): `09-observability-spans.md` defines a "retry rate per tool and per
# error_type" SLI, and `tool.retry` is its slot. Nothing computes it yet: deciding
# whether a call is a retry needs task-scoped history ("has this tool already errored
# under this task.id"), which is server-middleware state and deliberately not owned
# here — a per-call context manager has no business keeping a call log. The attribute
# defaults to False until that lands, so the SLI currently reads as a flat 0%. Feed it
# where task_id is tracked, not by giving this module memory.


@contextmanager
def tool_span(
    *,
    tool_name: str,
    mode: str,
    site: str | None = None,
    task_id: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> Generator[SpanMetrics]:
    """Wrap one tool call. Yields a metrics dict the tool fills in as it works.

    `mode` keeps live and fixture traffic separable — they are never mixed in a
    dashboard.
    """
    metrics: SpanMetrics = {}
    # `record_exception=False` is the load-bearing argument here, not a default worth
    # keeping. OpenTelemetry otherwise attaches an `exception` event carrying the
    # message and full stack trace, which routes straight around the SpanMetrics
    # whitelist — and exception messages in this codebase do carry payload-shaped
    # data (`UnknownMetricError` lists a group's metric names). The error *class* is
    # recorded below, which is the part a dashboard needs; the message is the part
    # that must not leave the process.
    # `set_status_on_exception` is off for the same reason: OTel fills the status
    # description with `f"{type}: {message}"`, message included. The status itself is
    # still set to ERROR below — the signal a backend reads, without the text.
    with tracer.start_as_current_span(
        SPAN_NAME, record_exception=False, set_status_on_exception=False
    ) as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("mode", mode)
        for key, value in (
            ("site", site),
            ("task.id", task_id),
            ("session.id", session_id),
            ("model", model),
        ):
            if value is not None:
                span.set_attribute(key, value)

        started = time.monotonic()
        try:
            yield metrics
        except Exception as exc:
            span.set_attribute("tool.success", False)
            span.set_attribute("tool.error_type", metrics.get("error_type", type(exc).__name__))
            # Status carries the class only. Nothing here interpolates `exc` itself.
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise
        else:
            span.set_attribute("tool.success", "error_type" not in metrics)
            if "error_type" in metrics:
                span.set_attribute("tool.error_type", metrics["error_type"])
        finally:
            span.set_attribute("tool.duration_ms", int((time.monotonic() - started) * 1000))
            if "data_status" in metrics:
                span.set_attribute("tool.data_status", metrics["data_status"])
            if "input_bytes" in metrics:
                span.set_attribute("tool.input_bytes", metrics["input_bytes"])
            if "output_bytes" in metrics:
                output_bytes = metrics["output_bytes"]
                span.set_attribute("tool.output_bytes", output_bytes)
                # Labeled an estimate in the schema; the bytes/4 heuristic is the
                # contract's own, not a measurement.
                span.set_attribute("tool.output_tokens_est", output_bytes // 4)
            if "page_index" in metrics:
                span.set_attribute("tool.page_index", metrics["page_index"])
            span.set_attribute("tool.retry", metrics.get("retry", False))
