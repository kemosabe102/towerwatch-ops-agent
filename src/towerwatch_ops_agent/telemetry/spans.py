"""One span per tool call (`docs/design/09-observability-spans.md`).

The no-secrets invariant is enforced structurally, not by review. `tool_span` never
receives a request or response object — only the primitives a caller writes into a
`SpanMetrics` TypedDict whose keys are fixed at type-check time. There is no code path
by which a payload value reaches `set_attribute`, so leaking is impossible rather than
merely filtered. A filter would need maintaining forever as new fields appear; this
needs nothing maintained.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TypedDict

from opentelemetry import trace

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
    with tracer.start_as_current_span(SPAN_NAME) as span:
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
