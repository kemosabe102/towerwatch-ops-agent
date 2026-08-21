"""`tool_span`'s own contract — no tool required.

These drive the context manager directly rather than through a real tool, so the
telemetry layer is verifiable in the PR that introduces it. The assertions that a
*specific* tool populates its span correctly belong to that tool's own tests
(`tests/tools/test_query_metrics_spans.py`), where a wrong `data_status` is the
tool's bug rather than this module's.
"""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from towerwatch_ops_agent.telemetry import spans as spans_module
from towerwatch_ops_agent.telemetry.spans import SPAN_NAME, tool_span


@pytest.fixture
def exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(spans_module, "tracer", provider.get_tracer("test"))
    return exporter


def _attrs(exporter: InMemorySpanExporter, index: int = 0) -> dict:
    return dict(exporter.get_finished_spans()[index].attributes or {})


def test_identity_attributes_are_always_present(exporter: InMemorySpanExporter) -> None:
    with tool_span(tool_name="towerwatch_query_metrics", mode="fixture", site="standstill"):
        pass
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})

    assert span.name == SPAN_NAME
    assert attrs["tool.name"] == "towerwatch_query_metrics"
    assert attrs["mode"] == "fixture"
    assert attrs["site"] == "standstill"
    assert attrs["tool.success"] is True
    assert isinstance(attrs["tool.duration_ms"], int)
    assert attrs["tool.retry"] is False


def test_mode_separates_fixture_from_live_traffic(exporter: InMemorySpanExporter) -> None:
    """Fixture and live traffic are never mixed in a dashboard, so mode is mandatory."""
    with tool_span(tool_name="t", mode="fixture"):
        pass
    with tool_span(tool_name="t", mode="live"):
        pass
    assert [_attrs(exporter, i)["mode"] for i in (0, 1)] == ["fixture", "live"]


def test_optional_identity_attributes_are_omitted_when_absent(
    exporter: InMemorySpanExporter,
) -> None:
    """Absent is absent — never the string 'None', which would pollute a group-by."""
    with tool_span(tool_name="t", mode="fixture"):
        pass
    attrs = _attrs(exporter)
    for key in ("site", "task.id", "session.id", "model"):
        assert key not in attrs


def test_metrics_written_by_the_caller_land_on_the_span(
    exporter: InMemorySpanExporter,
) -> None:
    with tool_span(tool_name="t", mode="fixture") as metrics:
        metrics["data_status"] = "ok"
        metrics["input_bytes"] = 40
        metrics["output_bytes"] = 120
    attrs = _attrs(exporter)

    assert attrs["tool.data_status"] == "ok"
    assert attrs["tool.input_bytes"] == 40
    assert attrs["tool.output_bytes"] == 120


def test_output_tokens_are_estimated_from_bytes(exporter: InMemorySpanExporter) -> None:
    """Labeled an estimate in the schema; the bytes/4 heuristic is the contract's own."""
    with tool_span(tool_name="t", mode="fixture") as metrics:
        metrics["output_bytes"] = 400
    assert _attrs(exporter)["tool.output_tokens_est"] == 100


def test_page_index_recorded_only_when_paging(exporter: InMemorySpanExporter) -> None:
    """Deep paging is a payload-design smell; it is only visible if the attribute is set."""
    with tool_span(tool_name="t", mode="fixture"):
        pass
    with tool_span(tool_name="t", mode="fixture") as metrics:
        metrics["page_index"] = 1

    assert "tool.page_index" not in _attrs(exporter, 0)
    assert _attrs(exporter, 1)["tool.page_index"] == 1


def test_error_type_marks_the_span_unsuccessful(exporter: InMemorySpanExporter) -> None:
    """A tool that returns an error envelope never raises, so success comes from the dict."""
    with tool_span(tool_name="t", mode="fixture") as metrics:
        metrics["error_type"] = "unknown_metric"
    attrs = _attrs(exporter)

    assert attrs["tool.success"] is False
    assert attrs["tool.error_type"] == "unknown_metric"


def test_an_escaping_exception_is_recorded_and_reraised(
    exporter: InMemorySpanExporter,
) -> None:
    """Nothing should escape a tool, but if it does the span must not claim success."""
    with pytest.raises(RuntimeError), tool_span(tool_name="t", mode="fixture"):
        raise RuntimeError("boom")
    attrs = _attrs(exporter)

    assert attrs["tool.success"] is False
    assert attrs["tool.error_type"] == "RuntimeError"


def test_duration_is_recorded_even_when_the_body_raises(
    exporter: InMemorySpanExporter,
) -> None:
    """A latency SLI blind to failures would hide the slowest calls in the system."""
    with pytest.raises(RuntimeError), tool_span(tool_name="t", mode="fixture"):
        raise RuntimeError("boom")
    assert isinstance(_attrs(exporter)["tool.duration_ms"], int)


def test_span_metrics_keys_are_closed() -> None:
    """The whitelist is the control — assert its exact shape so widening is deliberate."""
    assert set(spans_module.SpanMetrics.__annotations__) == {
        "data_status",
        "input_bytes",
        "output_bytes",
        "page_index",
        "retry",
        "error_type",
    }


def test_no_attribute_carries_a_payload_shaped_value(
    exporter: InMemorySpanExporter,
) -> None:
    """The structural no-secrets control, asserted end to end.

    `tool_span` accepts primitives from a fixed TypedDict, so there is no path for a
    measurement value or metric name to reach `set_attribute`. This pins that every
    attribute is a size, a class, or an identity — never contents.
    """
    with tool_span(tool_name="t", mode="fixture", site="standstill") as metrics:
        metrics["data_status"] = "ok"
        metrics["output_bytes"] = 120

    allowed = {
        "tool.name",
        "mode",
        "site",
        "tool.success",
        "tool.duration_ms",
        "tool.retry",
        "tool.data_status",
        "tool.output_bytes",
        "tool.output_tokens_est",
    }
    assert set(_attrs(exporter)) <= allowed


def test_tracer_is_reset() -> None:
    """Guards the monkeypatch: the module-level tracer is the real one outside tests."""
    assert isinstance(spans_module.tracer, trace.Tracer)
