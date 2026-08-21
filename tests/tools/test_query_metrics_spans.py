"""`query_metrics` populates its span correctly — the integration half.

`tool_span`'s own contract is tested in `tests/telemetry/test_spans.py` with no tool
involved. What is left, and what lives here, is whether *this tool* writes the right
values into it: the `data_status` a dashboard groups by, the error class an alert
fires on, and the guarantee that no measurement value reaches telemetry on the path a
real call actually takes.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from towerwatch_ops_agent.domain.fixture_client import FixtureClient
from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup, build_site_enum
from towerwatch_ops_agent.telemetry import spans as spans_module
from towerwatch_ops_agent.tools.query_metrics import (
    TOOL_NAME,
    build_request_model,
    query_metrics,
)


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


def test_a_successful_call_records_its_shape(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    _call(fixture_client)
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})

    assert attrs["tool.name"] == TOOL_NAME
    assert attrs["mode"] == "fixture"
    assert attrs["site"] == "standstill"
    assert attrs["tool.success"] is True
    assert attrs["tool.data_status"] == DataStatus.ok.value

    output_bytes = attrs["tool.output_bytes"]
    assert isinstance(output_bytes, int) and output_bytes > 0
    assert attrs["tool.output_tokens_est"] == output_bytes // 4
    input_bytes = attrs["tool.input_bytes"]
    assert isinstance(input_bytes, int) and input_bytes > 0


def test_absent_coverage_is_visible_on_the_span(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """A coverage regression shows up as a data_status mix shift, so it must be recorded."""
    _call(fixture_client, site="home", metric_group=MetricGroup.signal)
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})

    assert attrs["tool.data_status"] == DataStatus.not_collected.value
    assert attrs["tool.success"] is True  # an absence is a correct answer, not a failure


def test_empty_window_is_distinct_from_not_collected_on_the_span(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """The contract's load-bearing distinction has to survive into telemetry too."""
    _call(fixture_client, site="home", metric_group=MetricGroup.signal)
    _call(
        fixture_client,
        start="2026-07-14T02:00:00-07:00",
        end="2026-07-14T03:00:00-07:00",
    )
    absent, empty = (dict(s.attributes or {}) for s in exporter.get_finished_spans())

    assert absent["tool.data_status"] == DataStatus.not_collected.value
    assert empty["tool.data_status"] == DataStatus.empty_window.value


def test_an_error_envelope_marks_the_span_failed_with_its_class(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """The tool returns an envelope rather than raising, so success must come from it."""
    response = _call(fixture_client, metrics=["rtt_avg_bogus"])
    (span,) = exporter.get_finished_spans()
    attrs = dict(span.attributes or {})

    assert response.data_status is DataStatus.error
    assert attrs["tool.success"] is False
    assert attrs["tool.error_type"] == "unknown_metric"
    assert attrs["tool.data_status"] == DataStatus.error.value


def test_page_index_appears_only_on_a_continuation_call(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    first = _call(fixture_client, step="10m", page_size=4)
    _call(fixture_client, step="10m", page_size=4, page_token=first.next_page_token)
    unpaged, paged = (dict(s.attributes or {}) for s in exporter.get_finished_spans())

    assert "tool.page_index" not in unpaged
    assert paged["tool.page_index"] == 1


def test_no_measurement_value_reaches_telemetry_on_a_real_call(
    exporter: InMemorySpanExporter, fixture_client: FixtureClient
) -> None:
    """The no-secrets invariant on the path a real call takes.

    `tool_span`'s own test pins the attribute allowlist structurally. This is the
    end-to-end companion: a call that genuinely returns data must not leave any of
    that data, or the metric names carrying it, in the span.
    """
    response = _call(fixture_client)
    (span,) = exporter.get_finished_spans()
    rendered = " ".join(f"{k}={v}" for k, v in dict(span.attributes or {}).items())

    assert response.series  # the call really did return data to leak
    for metric_name, points in response.series.items():
        assert metric_name not in rendered
        for point in points:
            assert str(point.value) not in rendered
