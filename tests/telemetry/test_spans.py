"""Span emission and the no-secrets boundary."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from towerwatch_ops_agent.domain.fixture_client import FixtureClient
from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup, build_site_enum
from towerwatch_ops_agent.telemetry import spans as spans_module
from towerwatch_ops_agent.tools.query_metrics import build_request_model, query_metrics


@pytest.fixture
def exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(spans_module, "tracer", provider.get_tracer("test"))
    return exporter


def _call(fixture_client: FixtureClient, **overrides):
    model = build_request_model(build_site_enum(fixture_client.sites))
    params = {
        "site": "standstill",
        "metric_group": MetricGroup.latency,
        "start": "2026-07-14T00:00:00-07:00",
        "end": "2026-07-14T01:00:00-07:00",
    }
    params.update(overrides)
    return query_metrics(model(**params), client=fixture_client, mode="fixture")


def test_span_carries_the_required_attributes(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    _call(fixture_client)
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})

    assert span.name == "towerwatch.tool_call"
    assert attrs["tool.name"] == "towerwatch_query_metrics"
    assert attrs["tool.success"] is True
    assert attrs["mode"] == "fixture"
    assert attrs["site"] == "standstill"
    assert attrs["tool.data_status"] == DataStatus.ok.value
    assert isinstance(attrs["tool.duration_ms"], int)

    output_bytes = attrs["tool.output_bytes"]
    assert isinstance(output_bytes, int) and output_bytes > 0
    assert attrs["tool.output_tokens_est"] == output_bytes // 4
    assert attrs["tool.retry"] is False


def test_span_records_data_status_for_absent_groups(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """Coverage regressions show up as a data_status mix shift — so it must be on the span."""
    _call(fixture_client, site="home", metric_group=MetricGroup.signal)
    (span,) = exporter.get_finished_spans()
    assert dict(span.attributes or {})["tool.data_status"] == DataStatus.not_collected.value


def test_error_marks_success_false_with_a_machine_class(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    _call(fixture_client, metrics=["rtt_avg_bogus"])
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})
    assert attrs["tool.success"] is False
    assert attrs["tool.error_type"] == "unknown_metric"


def test_span_attributes_contain_no_payload_values(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """No measurement value or metric name may reach telemetry — sizes and classes only.

    Belt-and-suspenders: the primary control is that `tool_span` only ever receives
    primitives from a fixed TypedDict, so there is no path for a payload value to
    arrive. This test would catch someone widening that dict carelessly.
    """
    _call(fixture_client)
    (span,) = exporter.get_finished_spans()
    rendered = " ".join(f"{k}={v}" for k, v in dict(span.attributes or {}).items())

    for payload_value in ("101", "131", "rtt_avg_google", "pkt_loss_google"):
        assert payload_value not in rendered, f"{payload_value!r} leaked into span attributes"


def test_page_index_recorded_only_when_paging(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """Deep paging is a payload-design smell; it is only visible if the attribute is set."""
    first = _call(fixture_client, step="10m", page_size=4)
    _call(fixture_client, step="10m", page_size=4, page_token=first.next_page_token)
    unpaged, paged = exporter.get_finished_spans()

    assert "tool.page_index" not in dict(unpaged.attributes or {})
    assert dict(paged.attributes or {})["tool.page_index"] == 1


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


def test_tracer_is_reset() -> None:
    """Guards the monkeypatch: the module-level tracer is the real one outside tests."""
    assert isinstance(spans_module.tracer, trace.Tracer)
