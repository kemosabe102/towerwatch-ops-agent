"""The envelope's self-consistency guard.

`MetricSeriesResult.__post_init__` is the structural half of the repo's load-bearing
invariant: a model must be able to trust `data_status` over the shape of `metrics`.
These tests pin the contradictions it must refuse, so a second `DataClient`
implementation cannot reintroduce them quietly.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from towerwatch_ops_agent.domain.models import DataStatus, MetricGroup
from towerwatch_ops_agent.domain.protocol import (
    MetricSeriesResult,
    SeriesPoint,
    UnknownMetricError,
)

_PT = SeriesPoint(ts=datetime(2026, 7, 14, tzinfo=UTC), value=42.0)


@pytest.mark.parametrize("status", [DataStatus.not_collected, DataStatus.empty_window])
def test_absence_status_cannot_carry_series(status: DataStatus) -> None:
    """The exact contradiction the envelope exists to prevent."""
    with pytest.raises(ValueError, match="no data"):
        MetricSeriesResult(metrics={"rtt_avg_google": [_PT]}, data_status=status)


@pytest.mark.parametrize("status", [DataStatus.ok, DataStatus.partial])
def test_data_bearing_statuses_accept_series(status: DataStatus) -> None:
    result = MetricSeriesResult(metrics={"rtt_avg_google": [_PT]}, data_status=status)
    assert result.data_status is status


@pytest.mark.parametrize("status", [DataStatus.not_collected, DataStatus.empty_window])
def test_absence_status_with_empty_metrics_is_the_valid_case(status: DataStatus) -> None:
    """Absence is normal — only absence *with data* is the contradiction."""
    assert MetricSeriesResult(metrics={}, data_status=status).metrics == {}


def test_page_token_without_truncation_is_refused() -> None:
    """A token over a complete result would make a caller page forever."""
    with pytest.raises(ValueError, match="next_page_token"):
        MetricSeriesResult(
            metrics={"rtt_avg_google": [_PT]},
            data_status=DataStatus.ok,
            next_page_token="abc",
        )


def test_truncation_over_an_absence_is_refused() -> None:
    with pytest.raises(ValueError, match="nothing to continue"):
        MetricSeriesResult(metrics={}, data_status=DataStatus.empty_window, truncated=True)


def test_valid_truncated_page_is_accepted() -> None:
    result = MetricSeriesResult(
        metrics={"rtt_avg_google": [_PT]},
        data_status=DataStatus.ok,
        truncated=True,
        next_page_token="abc",
    )
    assert result.truncated and result.next_page_token == "abc"


def test_error_status_may_carry_no_metrics() -> None:
    """`error` is not an absence claim — it makes no assertion about coverage."""
    assert MetricSeriesResult(metrics={}, data_status=DataStatus.error).metrics == {}


def test_unknown_metric_error_carries_the_recovery_data() -> None:
    """The tool layer builds `retryable`/`suggested_next_call` from these fields."""
    exc = UnknownMetricError(
        metric_group=MetricGroup.latency,
        unknown=["rtt_avg_bogus"],
        valid=["rtt_avg_google"],
    )
    assert exc.unknown == ["rtt_avg_bogus"]
    assert exc.valid == ["rtt_avg_google"]
    assert "rtt_avg_google" in str(exc)
